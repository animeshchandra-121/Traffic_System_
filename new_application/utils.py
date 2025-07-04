# utils.py
# Canvas dimensions for frontend
CANVAS_WIDTH = 640   # frontend canvas width
CANVAS_HEIGHT = 360  # frontend canvas height

def letter_to_number(letter):
    """Convert signal letter (A,B,C,D) to number (1,2,3,4)"""
    mapping = {'A': 1, 'B': 2, 'C': 3, 'D': 4}
    return mapping.get(letter) - 1

def number_to_letter(number):
    """Convert signal number (1,2,3,4) to letter (A,B,C,D)"""
    return chr(ord('A') + number - 1)

def scale_points(points, actual_width, actual_height):
    """Scale points from frontend canvas size to actual video size."""
    return [
        [int(p[0] * actual_width / CANVAS_WIDTH), int(p[1] * actual_height / CANVAS_HEIGHT)]
        for p in points
    ]

def calculate_area_size(polygon_points):
    """Calculate the area of a polygon using the shoelace formula"""
    if len(polygon_points) < 3:
        return 0 # Default area if polygon is invalid
    
    n = len(polygon_points)
    area = 0
    for i in range(n):
        j = (i + 1) % n
        area += polygon_points[i][0] * polygon_points[j][1]
        area -= polygon_points[j][0] * polygon_points[i][1]
    return abs(area) / 2
