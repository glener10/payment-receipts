def scale_coordinates(
    coordinates, source_width, source_height, target_width, target_height
):
    scale_x = target_width / source_width
    scale_y = target_height / source_height

    scaled_coords = []
    for coord in coordinates:
        scaled_coords.append(
            {
                "x": int(coord["x"] * scale_x),
                "y": int(coord["y"] * scale_y),
                "width": int(coord["width"] * scale_x),
                "height": int(coord["height"] * scale_y),
            }
        )

    return scaled_coords
