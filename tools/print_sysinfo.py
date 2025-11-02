import sys, os
print('cwd=', os.getcwd())
print('sys.path[0]=', sys.path[0])
print('sys.path contains project root (has src dir):', any(os.path.isdir(os.path.join(p,'src')) for p in sys.path))
print('first 8 sys.path entries:')
for p in sys.path[:8]:
    print('  ', p)
print('src exists:', os.path.isdir('src'))
print('__file__ list under cwd:', os.listdir('.')[:20])
