import urllib.request
req = urllib.request.Request("https://c.incru.it/biz_file/2026/11/se2_1_20261124134717508.png", headers={"User-Agent": "Mozilla/5.0", "Referer": "https://job.incruit.com/"})
open("probe_tmp/post.png", "wb").write(urllib.request.urlopen(req, timeout=60).read())
print("saved")
