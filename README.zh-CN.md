# Impact Trail

**面向代码评审的 Python 变更影响分析。**

Impact Trail 是面向 Python 开发者和代码评审者的本地命令行工具。它从 Git 变更或手动指定的文件出发，沿静态导入图查找可能受影响的模块和候选测试文件，并为每个可达文件提供一条最短导入证据路径。

适用于提交 PR 前检查依赖、确定优先评审的文件，以及通过文本、JSON、Markdown 或离线 HTML 报告分享分析依据。

**无需 API Key，无运行时第三方依赖；分析在本地完成，不导入或执行被检查的 Python 项目。**

> 当前为 Alpha：文件级静态分析可能遗漏运行时依赖，也可能包含实际不影响行为的导入关系。候选测试文件仅供优先检查，不能作为安全筛选测试的依据。请保留项目要求的 CI 测试。

## 运行内置示例

需要 Python 3.10+。在源码目录执行：

```bash
git clone https://github.com/killerailian/impact-trail.git
cd impact-trail
python -m pip install .
impact-trail --root examples/shop --changed shop/pricing.py
impact-trail --root examples/shop --changed shop/pricing.py --format html --output report.html
```

打开 `report.html` 可以搜索文件、筛选测试并查看导入行号。报告仅包含路径和导入位置，不包含源代码正文；对外分享前仍需检查路径中的内部信息。

示例会发现两条测试依赖链：

```text
shop/pricing.py → shop/cart.py → tests/test_cart.py
shop/pricing.py → shop/cart.py → shop/api.py → tests/test_api.py
```

## 分析自己的项目

安装后，在目标 Git 仓库根目录执行：

```bash
impact-trail
impact-trail --base main --format markdown --output impact.md
impact-trail --format json --output impact.json
```

默认对比 HEAD 与工作区，包含已暂存、未暂存和未被忽略的未跟踪文件。`--base main` 对比的是 main 的确切提交，不会自动取分支共同祖先。

通过 `--source-root backend --source-root .` 指定导入根目录。默认存在 `src/` 时考虑 `src` 与 `.`，否则仅考虑 `.`。

`--changed path.py` 不需要 Git；若要保留删除文件的历史依赖，需要同时传入 `--base`。支持相对导入、包初始化、循环依赖和 pytest 的 conftest 目录作用域。

## 重要边界

- 输出的是文件级导入证据，不是函数调用图，也不是运行时覆盖率。
- 动态导入、插件、资源文件、环境变量和运行时路径调整可能导致漏报。
- 条件导入与类型检查导入也计入，可能产生误报。
- `candidate_tests` 仅供优先检查，不能据此省略其他测试。
- 解析失败、动态调用和不在图中的变更会提示警告；没有警告也不代表分析完整。
- `--strict` 遇到警告返回 2；成功返回 0；输入或 Git 错误返回 1。

尚未发布到 PyPI；请勿假定注册表中的同名包属于本项目。

运行测试：

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

[English](README.md) · [设计说明](docs/design.md) · [MIT 许可证](LICENSE)
