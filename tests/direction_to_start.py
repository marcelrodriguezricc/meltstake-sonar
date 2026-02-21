head_pos = -90
sector_start = -60
delta = ((head_pos - sector_start) % 360) - 180

if delta > 0:
    print("CCW")
elif delta < 0:
    print("CW")
else:
    print("Same direction")
