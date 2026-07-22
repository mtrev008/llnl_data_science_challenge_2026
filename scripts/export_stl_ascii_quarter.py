import argparse
import struct
from pathlib import Path


TRIANGLE = struct.Struct("<12fH")


def number(value: float) -> str:
    return format(value, ".9g")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--fraction", type=float, default=0.25)
    args = parser.parse_args()

    with args.source.open("rb") as source:
        source.read(80)
        triangle_count = struct.unpack("<I", source.read(4))[0]
        export_count = int(triangle_count * args.fraction)

        with args.destination.open("w", encoding="ascii", newline="\n") as output:
            output.write("solid quarter_sample_0_5\n")
            for _ in range(export_count):
                record = source.read(TRIANGLE.size)
                if len(record) != TRIANGLE.size:
                    raise EOFError("Unexpected end of binary STL")
                values = TRIANGLE.unpack(record)
                normal = " ".join(number(v) for v in values[0:3])
                vertex_1 = " ".join(number(v) for v in values[3:6])
                vertex_2 = " ".join(number(v) for v in values[6:9])
                vertex_3 = " ".join(number(v) for v in values[9:12])
                output.write(
                    f"  facet normal {normal}\n"
                    "    outer loop\n"
                    f"      vertex {vertex_1}\n"
                    f"      vertex {vertex_2}\n"
                    f"      vertex {vertex_3}\n"
                    "    endloop\n"
                    "  endfacet\n"
                )
            output.write("endsolid quarter_sample_0_5\n")

    print(f"source_triangles={triangle_count}")
    print(f"exported_triangles={export_count}")
    print(f"output={args.destination}")
    print(f"output_bytes={args.destination.stat().st_size}")


if __name__ == "__main__":
    main()
