data = open('app.py', 'r', encoding='utf-8').read()
old = 'sp.set_edgecolor("rgba(255,255,255,0.08)")'
new = 'sp.set_edgecolor("#ffffff")\n        sp.set_alpha(0.08)'
data = data.replace(old, new)
open('app.py', 'w', encoding='utf-8').write(data)
print("DONE")