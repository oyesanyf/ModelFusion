from PIL import Image

img = Image.open(r'd:\harfile\ModelFusion\reports\test_focus_screen.png')
w, h = img.size
candidates = []
for y in range(int(h * 0.2), int(h * 0.8)):
    for x in range(int(w * 0.1), int(w * 0.9)):
        r, g, b = img.getpixel((x, y))[:3]
        if b > 175 and r < 35 and 90 < g < 130:
            candidates.append((x, y))

# Group adjacent points into clusters
clusters = []
for pt in candidates:
    added = False
    for c in clusters:
        # Check if close to cluster bounding box
        if abs(pt[0] - c['cx']) < 60 and abs(pt[1] - c['cy']) < 30:
            c['pts'].append(pt)
            c['min_x'] = min(c['min_x'], pt[0])
            c['max_x'] = max(c['max_x'], pt[0])
            c['min_y'] = min(c['min_y'], pt[1])
            c['max_y'] = max(c['max_y'], pt[1])
            c['cx'] = (c['min_x'] + c['max_x']) // 2
            c['cy'] = (c['min_y'] + c['max_y']) // 2
            added = True
            break
    if not added:
        clusters.append({
            'pts': [pt],
            'min_x': pt[0], 'max_x': pt[0],
            'min_y': pt[1], 'max_y': pt[1],
            'cx': pt[0], 'cy': pt[1]
        })

print(f"Found {len(clusters)} clusters:")
for i, c in enumerate(clusters):
    bw = c['max_x'] - c['min_x']
    bh = c['max_y'] - c['min_y']
    if len(c['pts']) > 50 and 50 < bw < 250 and 15 < bh < 60:
        print(f"  Cluster {i}: Center=({c['cx']}, {c['cy']}) Size=({bw}, {bh}) Points={len(c['pts'])}")
