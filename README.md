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

### 在线更新的真实机制（2026-10-10 更新）

线上数据由 GitHub Actions 的 `Refresh live status & deploy Pages` 工作流抓取并部署。
**B 站风控按 IP 段拦截 Cloudflare 出口**：实测 GET/POST、带与不带 Cookie、经公共代理，全部返回 HTTP 412，
所以抓取不能放在 Cloudflare Worker 上；而 GitHub Actions 的出口一直正常（累计 2000+ 次成功运行）。

问题只出在“叫醒”：GitHub 自己的 `schedule` 是尽力而为，实测线上部署间隔漂到 **3 小时 54 分 ~ 7 小时 17 分**。
因此改为**从外部可靠地触发 `workflow_dispatch`**：

1. **云端定时（主力，24/7）**：Cloudflare Worker + Cron Trigger 每 5 分钟调用 GitHub API 触发同一个工作流，代码与步骤见 cron-trigger/ 目录；令牌只存在自己的 Cloudflare Secret 里。
2. **手动一键刷新（备用）**：双击桌面上的 刷新看板.cmd 立即触发一次，约 30 秒后再刷新页面即可；也可以在仓库 Actions 页面点 Run workflow。

`schedule` 保留作为兜底。工作流单次约 30 秒，只把状态数据放进部署产物，不改动仓库文件，不污染提交历史。
页面每 30 秒读取一次 `status.json`，并显示北京时间与“x 分钟前”。
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
