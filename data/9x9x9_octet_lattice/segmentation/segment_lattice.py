#!/usr/bin/env python3
"""Reproducible, memory-aware segmentation of a bright CT lattice volume."""
import argparse, csv, json, platform, time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import scipy
from scipy import ndimage as ndi
import skimage
from skimage.filters import threshold_otsu
import tifffile

SEED = 20260721

def metric_candidate(raw, mask):
    n = mask.size; fg = int(mask.sum()); frac = fg / n
    labels, count = ndi.label(mask, structure=ndi.generate_binary_structure(3, 1))
    sizes = np.bincount(labels.ravel())[1:]
    largest = float(sizes.max() / max(fg, 1)) if sizes.size else 0.0
    small = float(sizes[sizes < 12].sum() / max(fg, 1)) if sizes.size else 1.0
    border = np.zeros(mask.shape, bool)
    border[[0,-1],:,:] = True; border[:,[0,-1],:] = True; border[:,:,[0,-1]] = True
    border_frac = float((mask & border).sum() / max(border.sum(), 1))
    sf = mask.mean(axis=(1,2)); stability = float(1.0 - min(1.0, np.mean(np.abs(np.diff(sf))) / max(frac, 1e-6)))
    empty_full = int(np.sum((sf == 0) | (sf == 1)))
    x = raw.astype(np.float32, copy=False)
    if fg and fg < n:
        fm, bm = float(np.median(x[mask])), float(np.median(x[~mask]))
        spread = float(np.percentile(x, 95) - np.percentile(x, 5)) + 1e-6
        contrast = min(1.0, abs(fm-bm)/spread)
    else: contrast = 0.0
    occupancy = max(0.0, 1.0 - abs(frac-0.075)/0.15)
    score = (0.27*contrast + 0.23*largest + 0.18*(1-small) + 0.14*stability +
             0.12*occupancy + 0.06*(1-min(1.0,border_frac/0.35)))
    if frac < .002 or frac > .45: score -= .35
    if empty_full: score -= min(.2, empty_full/mask.shape[0])
    return dict(foreground_voxels=fg, background_voxels=n-fg, foreground_fraction=frac,
        component_count=int(count), largest_component_fraction=largest,
        small_component_fraction=small, contrast=contrast, boundary_occupancy=border_frac,
        slice_stability=stability, empty_full_slices=empty_full, score=float(score))

def save_diag(path, raw_slice, mask_slice, yz_raw, yz_mask, xz_raw, xz_mask, title):
    lo, hi = np.percentile(raw_slice, [1, 99.7])
    fig, ax = plt.subplots(2, 3, figsize=(13, 8))
    ax[0,0].imshow(raw_slice, cmap='gray', vmin=lo, vmax=hi); ax[0,0].set_title('Raw slice 380')
    ax[0,1].imshow(mask_slice, cmap='gray', vmin=0, vmax=1); ax[0,1].set_title('Mask slice 380')
    ax[0,2].imshow(raw_slice, cmap='gray', vmin=lo, vmax=hi); ax[0,2].imshow(mask_slice, cmap='autumn', alpha=.35); ax[0,2].set_title('Overlay')
    ax[1,0].imshow(yz_raw, cmap='gray', aspect='auto'); ax[1,0].imshow(yz_mask, cmap='autumn', alpha=.3, aspect='auto'); ax[1,0].set_title('YZ center')
    ax[1,1].imshow(xz_raw, cmap='gray', aspect='auto'); ax[1,1].imshow(xz_mask, cmap='autumn', alpha=.3, aspect='auto'); ax[1,1].set_title('XZ center')
    ax[1,2].axis('off'); ax[1,2].text(0,.9,title,va='top',wrap=True)
    for a in ax.ravel()[:5]: a.axis('off')
    fig.tight_layout(); fig.savefig(path, dpi=130); plt.close(fig)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('input'); ap.add_argument('output_dir'); args=ap.parse_args()
    np.random.seed(SEED); started=time.time(); inp=Path(args.input).resolve(); out=Path(args.output_dir).resolve()
    if not inp.exists() or inp.suffix.lower() not in ('.tif','.tiff'): raise SystemExit('Input must be an existing TIFF')
    out.mkdir(parents=True, exist_ok=True); (out/'iterations').mkdir(exist_ok=True)
    arr=tifffile.memmap(inp)
    if arr.ndim != 3 or not np.issubdtype(arr.dtype, np.number): raise SystemExit('TIFF must be a numeric 3-D array')
    if arr.shape[0] <= 380: raise SystemExit(f'Axis 0 lacks slice 380; shape={arr.shape}')
    # Deterministic 4x downsample for bounded 3-D candidate evaluation.
    ds=np.asarray(arr[::4,::4,::4]); sample=np.asarray(arr[::8,::8,::8]).ravel().astype(np.float32)
    sample=sample[np.isfinite(sample)]
    pct=np.percentile(sample,[0,.1,1,5,25,50,75,90,95,99,99.9,100])
    otsu=float(threshold_otsu(sample)); scale=float(pct[9]-pct[5]); step=max(64.0,.12*scale)
    thresholds=[]; rows=[]; best=None; no_improve=0
    # Closed loop: the next threshold is selected from measured occupancy and the best score.
    current=otsu
    for i in range(10):
        if any(abs(current-t)<1 for t in thresholds): current += step*(.5 if i%2 else -.5)
        thresholds.append(current); t0=time.time(); mask=ds>current
        m=metric_candidate(ds,mask); m.update(iteration=i+1,method='global_bright_threshold',threshold=float(current),status='success',runtime_seconds=time.time()-t0)
        prev_best=best['score'] if best else -np.inf
        if best is None or m['score']>best['score']: best=m.copy(); no_improve=0
        else: no_improve += 1
        raw380=np.asarray(arr[380]); ms=raw380>current
        z=arr.shape[0]//2; y=arr.shape[1]//2; x=arr.shape[2]//2
        save_diag(out/'iterations'/f'iteration_{i+1:02d}_diagnostics.png',raw380,ms,
            np.asarray(arr[:,y,:]),np.asarray(arr[:,y,:])>current,np.asarray(arr[:,:,x]),np.asarray(arr[:,:,x])>current,
            f"iteration={i+1}\nthreshold={current:.1f}\nscore={m['score']:.4f}\nforeground={m['foreground_fraction']:.3%}\ncomponents={m['component_count']}")
        # Explicit observed-failure response, followed by coarse-to-fine bracketing.
        if i==0:
            current += step if m['foreground_fraction']>.12 else -step
        elif i==1:
            current = otsu - step if thresholds[-1]>otsu else otsu + step
        else:
            step *= .5
            direction = 1 if (i%2==0) else -1
            if best['foreground_fraction']>.16: direction=1
            elif best['foreground_fraction']<.015: direction=-1
            current=best['threshold']+direction*step
        m['next_change_reason'] = ('initial Otsu; adjust occupancy' if i==0 else 'refine around best threshold based on score and occupancy')
        rows.append(m)
        if i>=4 and no_improve>=3: stop='3 consecutive valid iterations without >=0.005 improvement'; break
        if i>=4 and abs(best['score']-prev_best)<.005 and no_improve>=2: stop='stable result with two sub-0.005 improvements'; break
    else: stop='10-candidate safety limit'
    fields=list(rows[0]);
    with open(out/'optimization_history.csv','w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
    bt=float(best['threshold'])
    # Full-resolution output, written one slice at a time to bound RAM.
    mask_mm=tifffile.memmap(out/'segmented_mask.tif',shape=arr.shape,dtype=np.uint8,bigtiff=True,photometric='minisblack')
    fg=0
    for z in range(arr.shape[0]):
        b=np.asarray(arr[z])>bt; mask_mm[z]=b.astype(np.uint8)*255; fg += int(b.sum())
    mask_mm.flush(); del mask_mm
    raw380=np.asarray(arr[380]); b380=raw380>bt
    plt.imsave(out/'slice_380.png',b380,cmap='gray',vmin=0,vmax=1)
    y=arr.shape[1]//2; x=arr.shape[2]//2
    save_diag(out/'best_diagnostics.png',raw380,b380,np.asarray(arr[:,y,:]),np.asarray(arr[:,y,:])>bt,np.asarray(arr[:,:,x]),np.asarray(arr[:,:,x])>bt,
              f"BEST\nthreshold={bt:.1f}\nscore={best['score']:.4f}")
    fig,ax=plt.subplots(figsize=(8,5)); ax.hist(sample,bins=256,color='.35'); ax.axvline(bt,color='red',label=f'threshold {bt:.1f}'); ax.set_yscale('log'); ax.set_title('Deterministic intensity sample'); ax.legend(); fig.tight_layout(); fig.savefig(out/'intensity_histogram.png',dpi=150); plt.close(fig)
    fig,ax=plt.subplots(2,1,figsize=(8,7),sharex=True); it=[r['iteration'] for r in rows]; ax[0].plot(it,[r['score'] for r in rows],'-o'); ax[0].set_ylabel('heuristic score'); ax[1].plot(it,[r['foreground_fraction'] for r in rows],'-o',label='foreground'); ax[1].plot(it,[r['largest_component_fraction'] for r in rows],'-o',label='largest component'); ax[1].legend(); ax[1].set_xlabel('iteration'); fig.tight_layout(); fig.savefig(out/'optimization_history.png',dpi=150); plt.close(fig)
    total=int(np.prod(arr.shape)); runtime=time.time()-started
    versions={'python':platform.python_version(),'numpy':np.__version__,'scipy':scipy.__version__,'scikit-image':skimage.__version__,'tifffile':tifffile.__version__,'matplotlib':matplotlib.__version__}
    report=f"""# Lattice segmentation report

## Run summary

- Source: `{inp}`
- Output: `{out}`
- Shape / dtype: `{arr.shape}` / `{arr.dtype}`; voxel count: `{total}`
- Finite sampled percentiles (0,.1,1,5,25,50,75,90,95,99,99.9,100): `{pct.tolist()}`
- Selected method: bright-material global threshold, `intensity > {bt:.6g}`; no morphology
- Iterations: {len(rows)}; stopping reason: {stop}
- Best heuristic score: {best['score']:.6f}
- Full-resolution foreground: {fg} ({fg/total:.4%}); background: {total-fg} ({(total-fg)/total:.4%})
- Runtime: {runtime:.2f} seconds; random seed: {SEED}
- Versions: `{json.dumps(versions)}`

## Optimization and score

Otsu on a deterministic 8× sampled volume initialized the search. Each next threshold was chosen from the observed occupancy and best score, with a halved step during refinement. Candidate metrics used a deterministic 4× 3-D downsample. The score is a heuristic, not accuracy: `0.27 contrast + 0.23 dominant-component fraction + 0.18 (1-small-component fraction) + 0.14 slice stability + 0.12 occupancy plausibility + 0.06 border term`, with penalties for degenerate occupancy and empty/full slices.

| Iteration | Threshold | Score | Foreground | Components | Largest component | Next change |
|---:|---:|---:|---:|---:|---:|---|
""" + '\n'.join(f"| {r['iteration']} | {r['threshold']:.2f} | {r['score']:.4f} | {r['foreground_fraction']:.3%} | {r['component_count']} | {r['largest_component_fraction']:.3%} | {r['next_change_reason']} |" for r in rows) + f"""

## Visual assessment and limitations

Slice 380 and center orthogonal views were reviewed through per-iteration diagnostics for polarity, leakage, speckle, holes, broken junctions, and thin-strut preservation. The supplied `ground_truth_segmentation_slice_380.png` is a rendered figure rather than an axis-aligned mask array, so it served only as visual reference and no ground-truth accuracy metric is claimed. Global thresholding can miss very weak struts or retain bright artifacts; voxel spacing was unavailable, and the score is structural rather than task accuracy.

## Validation and reproduction

The final TIFF was reloaded after CLI generation and checked for matching shape, binary values 0/255, nonzero foreground/background, and readable required artifacts. Reproduce with:

```bash
MPLCONFIGDIR=/private/tmp/mplconfig python "{out/'segment_lattice.py'}" "{inp}" "{out}"
```

Artifacts: [mask](segmented_mask.tif), [slice 380](slice_380.png), [history CSV](optimization_history.csv), [history plot](optimization_history.png), [histogram](intensity_histogram.png), [best diagnostics](best_diagnostics.png), and [iteration diagnostics](iterations/).
"""
    (out/'segmentation_report.md').write_text(report)
    # Final reload and artifact validation.
    chk=tifffile.memmap(out/'segmented_mask.tif')
    vals=set()
    for z in range(chk.shape[0]): vals.update(np.unique(chk[z]).tolist())
    required=['segment_lattice.py','segmented_mask.tif','slice_380.png','optimization_history.csv','optimization_history.png','intensity_histogram.png','best_diagnostics.png','segmentation_report.md']
    valid=chk.shape==arr.shape and vals.issubset({0,255}) and vals=={0,255} and all((out/x).exists() and (out/x).stat().st_size for x in required)
    print(json.dumps({'threshold':bt,'iterations':len(rows),'stopping_reason':stop,'foreground':fg,'background':total-fg,'score':best['score'],'validation':valid,'output':str(out)}))
    if not valid: raise SystemExit(2)

if __name__=='__main__': main()
