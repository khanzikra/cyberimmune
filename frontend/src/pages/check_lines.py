with open('sample-logs.vue', 'r') as f:
    lines = f.readlines()
    for i, line in enumerate(lines[360:370], 360):
        print(str(i) + ': ' + repr(line))