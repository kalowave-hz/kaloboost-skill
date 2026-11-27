# kaloboost-skill 仓库规则

## 发版流程（每次发版都要做完四步）

本仓库没有 CI/CD，GitHub Release 不触发任何流程。用户经 `npx skills add kalowave-hz/kaloboost-skill` 直接从仓库安装；升级提示（`skills/kaloboost/scripts/kaloboost/update.py`）用 `git ls-remote` 读最新 tag 与本地 `__version__` 比较。

1. 版本号：改 `skills/kaloboost/scripts/kaloboost/__init__.py` 的 `__version__`（随功能 PR 或单独的 `Release x.y.z` PR）。
2. 合入 `main`。
3. 在合入提交上打 annotated tag `vX.Y.Z` 并推送：`git tag -a vX.Y.Z <commit> -m "Release X.Y.Z: <一句话>" && git push origin vX.Y.Z`。
4. **建 GitHub Release**（2026-11-27 felix 定，格式照 sailtonight 的 v0.5.0 / v0.6.0）：`gh release create vX.Y.Z --repo kalowave-hz/kaloboost-skill --verify-tag --title vX.Y.Z --notes-file <notes> --latest`。正文英文、三段：

   ```markdown
   ## Changes
   - **<功能名>** (`boost <command>`, alias `<alias>`): <做什么、关键参数、只读 / 写、限制>.
   - <其它要点：错误提示、SKILL.md 新增的使用说明、MCP 工具的只读 / 写 / destructive 标注>.

   ## Upgrade
   `npx skills add kalowave-hz/kaloboost-skill` (add `-g` for a global install). For MCP, restart the `uvx` server.

   **Full changelog**: https://github.com/kalowave-hz/kaloboost-skill/compare/v<上一版>...vX.Y.Z
   ```
