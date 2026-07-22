import struct
import math


def compute_normal(v1, v2, v3):
    """Compute a normalized normal vector for a triangle."""

    ux = v2[0] - v1[0]
    uy = v2[1] - v1[1]
    uz = v2[2] - v1[2]

    vx = v3[0] - v1[0]
    vy = v3[1] - v1[1]
    vz = v3[2] - v1[2]

    # Cross product: u × v
    nx = uy * vz - uz * vy
    ny = uz * vx - ux * vz
    nz = ux * vy - uy * vx

    # Normalize the normal vector
    length = math.sqrt(nx * nx + ny * ny + nz * nz)

    if length == 0:
        return 0.0, 0.0, 0.0

    return nx / length, ny / length, nz / length


def write_binary_stl(filename, triangles):
    """Write a collection of triangles to a binary STL file."""

    with open(filename, "wb") as file:
        # Binary STL files begin with an 80-byte header
        title = b"Python Binary STL Example"
        header = title + b"\0" * (80 - len(title))
        file.write(header)

        # Write the number of triangles as a 4-byte unsigned integer
        file.write(struct.pack("<I", len(triangles)))

        for v1, v2, v3 in triangles:
            normal = compute_normal(v1, v2, v3)

            # 3 normal floats
            # 9 vertex floats
            # 1 unsigned short attribute count
            data = struct.pack(
                "<3f3f3f3fH",
                *normal,
                *v1,
                *v2,
                *v3,
                0
            )

            file.write(data)


# Pyramid with a square base
triangles = [
    # Base
    ((0, 0, 0), (1, 0, 0), (1, 1, 0)),
    ((0, 0, 0), (1, 1, 0), (0, 1, 0)),

    # Four sides
    ((0, 0, 0), (1, 0, 0), (0.5, 0.5, 1)),
    ((1, 0, 0), (1, 1, 0), (0.5, 0.5, 1)),
    ((1, 1, 0), (0, 1, 0), (0.5, 0.5, 1)),
    ((0, 1, 0), (0, 0, 0), (0.5, 0.5, 1)),
]


write_binary_stl("pyramid.stl", triangles)
print("Binary STL 'pyramid.stl' created.")