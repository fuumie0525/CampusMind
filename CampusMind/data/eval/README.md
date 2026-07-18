# Evaluation Data

`POST /eval/run` 会运行校园意图识别与 LLM-as-Judge 对话质量评测。
首次运行后，系统会在此目录生成 `baseline.json`，后续版本与该基线比较并检测超过 5% 的指标回退。

请不要把包含真实学生对话、学号或联系方式的评测文件提交到公开仓库。
