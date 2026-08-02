# Application requirements JSON contract

Create `application_requirements.json` with this structure. Every top-level
requirement key is mandatory even when its value is unknown.

```json
{
  "schema_version": "1.0.0",
  "status": "incomplete",
  "intended_function": null,
  "material": {
    "designation": null,
    "condition_or_grade": null,
    "properties_source": null
  },
  "loading": {
    "type": [],
    "magnitude": [],
    "direction": null,
    "service_mode": []
  },
  "boundary_and_attachment_conditions": null,
  "safety_or_criticality_classification": null,
  "environment_and_expected_life": {
    "environment": null,
    "expected_life": {
      "value": null,
      "unit": null
    },
    "duty_cycle": null
  },
  "allowable_deformation": {
    "value": null,
    "unit": null,
    "basis": null
  },
  "consequence_of_failure": null,
  "applicable_industry_and_jurisdiction": {
    "industry": null,
    "jurisdiction": null,
    "codes_and_standards": []
  },
  "sources": [],
  "assumptions": [],
  "notes": [],
  "missing_required_fields": [],
  "revision_history": []
}
```

## Field rules

- `loading.type`: describe physical loading such as tension, compression,
  bending, torsion, pressure, shear, or combined loading.
- `loading.magnitude`: use objects with `value`, `unit`, and optional
  `range_or_case`; do not store an unqualified number.
- `loading.direction`: state the coordinate system or component reference.
- `loading.service_mode`: use one or more of `static`, `cyclic`, `impact`, or
  `thermal`; add another explicit mode only when required.
- `environment_and_expected_life`: capture temperature, corrosion, radiation,
  vacuum, humidity, chemical, wear, or other relevant exposure plus design
  life and duty cycle.
- `allowable_deformation`: distinguish displacement, strain, rotation,
  dimensional tolerance, or other governing measure in `basis`.
- `sources`: use objects containing `field`, `source`, and, when available,
  `location` and `retrieved_at`.
- `assumptions`: may document analysis assumptions but must not satisfy a
  required field or change `status` to `complete`.
- `missing_required_fields`: use JSON Pointer-like paths such as
  `/loading/direction`.
- `revision_history`: use objects containing `timestamp`, `author_or_source`,
  `changed_fields`, and `reason`.

The eleven required application topics are intended function, material,
loading type, load magnitude and direction, service mode, boundary and
attachment conditions, safety or criticality classification, environment and
expected life, allowable deformation, consequence of failure, and applicable
industry and jurisdiction.
