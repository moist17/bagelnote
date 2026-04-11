import urllib.request, os

os.makedirs('/Users/lizchen/Projects/bagelnote-astro/public/sketchbook', exist_ok=True)

imgs = [
    ('img_2337.jpg', 'https://bagelnote.wordpress.com/wp-content/uploads/2023/11/img_2337.jpg'),
    ('img_2339.jpg', 'https://bagelnote.wordpress.com/wp-content/uploads/2023/11/img_2339.jpg'),
    ('img_2298.jpg', 'https://bagelnote.wordpress.com/wp-content/uploads/2023/11/img_2298.jpg'),
    ('img_2338.jpg', 'https://bagelnote.wordpress.com/wp-content/uploads/2023/11/img_2338.jpg'),
    ('page0.jpg', 'https://bagelnote.wordpress.com/wp-content/uploads/2023/11/page0.jpg'),
    ('page0-2.jpg', 'https://bagelnote.wordpress.com/wp-content/uploads/2023/11/page0-2.jpg'),
]

for name, url in imgs:
    path = f'/Users/lizchen/Projects/bagelnote-astro/public/sketchbook/{name}'
    urllib.request.urlretrieve(url, path)
    print(f'下載完成：{name}')
