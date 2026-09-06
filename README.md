# VirtuaReal / P-SP 实时开播看板

自动更新，不用你手动刷时间。

## 本机实时网站（现在就能用）

1. 双击 **`start-live.bat`**（只要这个，纯英文，不会乱码）
2. 浏览器会打开 `http://127.0.0.1:8765/`
3. **黑窗口一直开着** = 后台约每 45 秒问一次 B 站；网页约每 10 秒自动重画
4. 关掉黑窗口 = 停止更新

不要双击 `index.html` / 旧的中文 bat（在中文版 CMD 会乱码报错）。

## 做成「大家打开链接就能看」的公开网站

浏览器网页**不能直接**访问 B 站接口（跨域），所以公开站必须靠服务器定时刷新。免费做法：

1. 把本文件夹推到 GitHub 公开仓库  
2. Settings → Pages → Source 选 **GitHub Actions**  
3. Actions 跑 **Refresh live status & deploy Pages**  
4. 之后约每 10 分钟自动更新，访客只打开 Pages 链接即可  

公开站延迟大约几分钟到十几分钟（GitHub 定时任务本身会漂）。  
本机 `start-live.bat` 更接近实时（约 45 秒级）。

## 文件

| 文件 | 作用 |
|---|---|
| `start-live.bat` | 一键开实时网站（推荐） |
| `live.html` | 实时看板页 |
| `scripts/live_site.py` | 本机自动刷新服务 |
| `scripts/monitor.py` | 查询 B 站开播 |
| `roster.json` | VR / PSP 名单 |
| `.github/workflows/` | 公开站定时部署 |

## 声明

非官方、非商业。名单来自 [vtbs.moe VDB](https://vdb.vtbs.moe/)，状态来自 B 站公开接口。请保持合理刷新间隔。
