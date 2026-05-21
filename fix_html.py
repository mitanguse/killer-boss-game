import re

path = r'C:\Users\iamgo\.openclaw\workspace\projects\killer-boss-game\frontend\index.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Find the 天数 stat card and add intel display after it
old = '''                    <div class="stat-card" style="border-color:var(--accent-purple);">
                        <div class="label">📅 天数</div>
                        <div class="big-value" id="stat-day" style="color:var(--accent-purple);">第 1 天</div>
                    </div>'''

new = '''                    <div class="stat-card" style="border-color:var(--accent-purple);">
                        <div class="label">📅 天数</div>
                        <div class="big-value" id="stat-day" style="color:var(--accent-purple);">第 1 天</div>
                    </div>

                    <div class="stat-card" style="border-color:var(--accent-gold);">
                        <div class="label">📡 情报</div>
                        <div class="big-value" id="stat-intel" style="color:var(--accent-gold);">0</div>
                    </div>'''

if old in content:
    content = content.replace(old, new, 1)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('OK - intel element added to index.html')
else:
    print('ERROR: Could not find the target section')
    # debug
    idx = content.find('天数')
    if idx >= 0:
        print(content[idx-50:idx+100])
