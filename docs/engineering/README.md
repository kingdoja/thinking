# 工程文档索引

本目录包含项目的工程技术文档。

## 📚 文档列表

### 核心架构文档
- **[SYSTEM-BLUEPRINT.md](./SYSTEM-BLUEPRINT.md)** - 系统架构蓝图
  - 系统边界和模块划分
  - 数据模型设计
  - 运行时职责
  - 工作流编排

- **[DELIVERY-PLAN.md](./DELIVERY-PLAN.md)** - 交付计划
  - 6 个迭代的详细规划
  - 任务依赖关系
  - 验收标准（DoD）
  - 里程碑定义

### 迭代进度文档
- **[ITERATION2_NEXT_STEPS.md](./ITERATION2_NEXT_STEPS.md)** - Iteration 2 完成总结和下一步指南
  - 完成度总结
  - 验证结果
  - 下一步行动计划
  - 常见问题解答

### API 契约文档
- **API-CONTRACT.md** - API 接口契约（待创建）
- **WORKFLOW-CONTRACT.md** - 工作流契约（待创建）
- **AGENT-CONTRACT.md** - Agent 契约（待创建）

## 📁 文档组织结构

```
docs/
├── engineering/          # 工程技术文档（本目录）
│   ├── SYSTEM-BLUEPRINT.md
│   ├── DELIVERY-PLAN.md
│   ├── ITERATION2_NEXT_STEPS.md
│   └── README.md
├── product/             # 产品文档
├── design/              # 设计文档
└── interview/           # 面试准备材料
```

## 🔗 相关文档

### 项目根目录
- **[README.md](../../README.md)** - 项目总览
- **[PROJECT_SUMMARY.md](../../PROJECT_SUMMARY.md)** - 项目总结

### Spec 文档
- **[.kiro/specs/text-pipeline-mock/](../../.kiro/specs/text-pipeline-mock/)** - 文本主链路 Spec
  - requirements.md - 需求文档
  - design.md - 设计文档
  - tasks.md - 任务列表
  - ITERATION2_COMPLETION_REPORT.md - Iteration 2 完成报告

- **[.kiro/specs/code-refactor/](../../.kiro/specs/code-refactor/)** - 代码重构 Spec

### API 文档
- **[apps/api/QUICKSTART.md](../../apps/api/QUICKSTART.md)** - 快速开始指南
- **[apps/api/TROUBLESHOOTING.md](../../apps/api/TROUBLESHOOTING.md)** - 故障排查指南
- **[apps/api/E2E_TEST_GUIDE.md](../../apps/api/E2E_TEST_GUIDE.md)** - 端到端测试指南

### Agent Runtime 文档
- **[workers/agent-runtime/README.md](../../workers/agent-runtime/README.md)** - Agent Runtime 说明
- **[workers/agent-runtime/docs/](../../workers/agent-runtime/docs/)** - Agent 详细文档

## 📊 当前项目状态

**当前迭代**: Iteration 2 ✅ 已完成  
**下一迭代**: Iteration 3 - Storyboard 到 Asset 工作台

**里程碑进度**:
- ✅ M1: 文本链路走到 storyboard，workspace 可显示真实 documents 与 shots
- ⏳ M2: preview 可生成，资产入库可见
- ⏳ M3: QA / review / rerun / export 闭环可用
- ⏳ M4: 样板项目稳定重复运行，系统可以进入 pilot 试用

## 🚀 快速导航

### 我想了解...
- **系统整体架构** → [SYSTEM-BLUEPRINT.md](./SYSTEM-BLUEPRINT.md)
- **开发计划和进度** → [DELIVERY-PLAN.md](./DELIVERY-PLAN.md)
- **当前应该做什么** → [ITERATION2_NEXT_STEPS.md](./ITERATION2_NEXT_STEPS.md)
- **如何运行项目** → [apps/api/QUICKSTART.md](../../apps/api/QUICKSTART.md)
- **遇到问题怎么办** → [apps/api/TROUBLESHOOTING.md](../../apps/api/TROUBLESHOOTING.md)

### 我想开发...
- **新的 Agent** → [workers/agent-runtime/README.md](../../workers/agent-runtime/README.md)
- **新的 API 端点** → [SYSTEM-BLUEPRINT.md](./SYSTEM-BLUEPRINT.md) 第 12 节
- **新的功能** → 先查看 [DELIVERY-PLAN.md](./DELIVERY-PLAN.md) 确认优先级

---

**最后更新**: 2026-04-07  
**维护者**: 项目团队
