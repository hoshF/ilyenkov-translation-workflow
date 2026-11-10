# 文章教学示例：比较与区别

[`sravnenie-i-razlichie.md`](sravnenie-i-razlichie.md) 是为本项目新编的俄文短文，供练习单篇文章流程。它不是已发表的作品，没有示范译文、真实审阅记录或 Owner 裁决。许可和署名状态见[项目许可说明](../../README.md#许可与署名)。

原文按单篇文章的形态写成：front matter 依 [`STRUCTURE.md`](../../STRUCTURE.md)，正文有引言段、两个带罗马数字编号的小节和一条注释，可以练习小节编号写法、引言标题规范化和注释编号。

`text_status` 为 `html_conversion_unverified`，沿用[既有数字文本流程](../../digitization/EXISTING_DIGITAL_TEXT_WORKFLOW.md)的未核验状态名；本例没有进行 HTML 转换，也没有完成底本验收。练习翻译时，Owner 在任务指令中授权使用这一未核验教学输入，并按[文章流程](../../translation/ARTICLE_TRANSLATION_WORKFLOW.md)把风险记入 handoff。

建立练习项目：

```bash
python3 scripts/new_project.py article ../translation-practice --work-id sravnenie-i-razlichie --title "Сравнение и различие" --title-zh "比较与区别" --source examples/article/sravnenie-i-razlichie.md
```

此后按[任务指令模板](../../AGENT_TASKS.md)第 2—4 节进行。
