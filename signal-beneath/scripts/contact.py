import sys, glob, os, subprocess
d = sys.argv[1]
files = sorted(f for f in glob.glob(os.path.join(d, '*.jpg')) if not os.path.basename(f).startswith('contact'))
for k in range(0, len(files), 12):
    chunk = files[k:k + 12]
    args = ['ffmpeg', '-y', '-loglevel', 'error']
    for f in chunk: args += ['-i', f]
    n = len(chunk)
    fc = ''.join(f'[{i}:v]scale=270:480[s{i}];' for i in range(n)) + ''.join(f'[s{i}]' for i in range(n)) + f'xstack=inputs={n}:layout=' + '|'.join(f'{(i % 6) * 270}_{(i // 6) * 480}' for i in range(n)) + (':fill=black' if n < 12 else '')
    if n == 1: fc = '[0:v]scale=270:480'
    subprocess.run(args + ['-filter_complex', fc, os.path.join(d, f'contact_{k // 12:02d}.jpg')], check=True)
print('[contact] sheets written')
