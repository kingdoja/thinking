# 文档组织说明

**日期**: 2026-04-07  
**目的**: 说明项目文档的组织结构和位置

---

## 📁 文档目录结构

```
项目根目录/
│
├── README.md                          # 项目总览
├── PROJECT_SUMMARY.md                 # 项目总结
│
├── docs/                              # 文档目录
│   ├── engineering/                   # 工程技术文档
│   │   ├── README.md                 # 工程文档索引
│   │   ├── SYSTEM-BLUEPRINT.md       # 系统架构蓝图
│   │   ├── DELIVERY-PLAN.md          # 交付计划
│   │   ├── ITERATION2_NEXT_STEPS.md  # Iteration 2 总结和下一步
│   │   └── DOCUMENT_ORGANIZATION.md  # 本文档
│   │
│   ├── product/                       # 产品文档
│   ├── design/                        # 设计文档
│   └── interview/                     # 面试准备材料
│
├── .kiro/specs/                       # 功能规格文档
│   ├── text-pipeline-mock/           # 文本主链路 Spec
│   │   ├── requirements.md           # 需求文档
│   │   ├── design.md                 # 设计文档
│   │   ├── tasks.md                  # 任务列表
│   │   └── ITERATION2_COMPLETION_REPORT.md  # Iteration 2 完成报告
│   │
│   └── code-refactor/                # 代码重构 Spec
│       ├── requirements.md
│       ├── design.md
│       └── tasks.md
│
├── apps/api/                          # API 应用
│   ├── QUICKSTART.md                 # 快速开始指南
│   ├── TROUBLESHOOTING.md            # 故障排查指南
│   ├── E2E_TEST_GUIDE.md             # 端到端测试指南
│   │
│   └── tests/                        # 测试文件
│       ├── test_workflow_simple.py   # 工作流简单验证
│       ├── test_full_workflow.py     # 完整工作流测试
│       └── ...
│
└── workers/agent-runtime/             # Agent Runtime
    ├── README.md                     # Agent Runtime 说明
    └── docs/                         # Agent 详细文档
        └── MIGRATION.md              # 迁移指南
```

---

## 📋 文档分类

### 1. 项目级文档（根目录）
**位置**: 项目根目录  
**用途**: 项目概览和快速了解

- `README.md` - 项目介绍、架构概览、快速开始
- `PROJECT_SUMMARY.md` - 项目总结、技术栈、完成功能
- `README.en.md` - 英文版 README

### 2. 工程技术文档
**位置**: `docs/engineering/`  
**用途**: 系统设计、架构、开发计划

- `SYSTEM-BLUEPRINT.md` - 系统架构总图
- `DELIVERY-PLAN.md` - 6 个迭代的详细计划
- `ITERATION2_NEXT_STEPS.md` - 当前进度和下一步行动
- `README.md` - 工程文档索引

### 3. 功能规格文档
**位置**: `.kiro/specs/`  
**用途**: 具体功能的需求、设计、任务

每个功能一个子目录，包含：
- `requirements.md` - 需求文档（EARS 格式）
- `design.md` - 设计文档（包含正确性属性）
- `tasks.md` - 任务列表（可执行的开发任务）
- 其他相关文档（如完成报告）

### 4. API 应用文档
**位置**: `apps/api/`  
**用途**: API 使用指南、故障排查

- `QUICKSTART.md` - 如何快速启动项目
- `TROUBLESHOOTING.md` - 常见问题和解决方案
- `E2E_TEST_GUIDE.md` - 如何运行端到端测试

### 5. Agent Runtime 文档
**位置**: `workers/agent-runtime/`  
**用途**: Agent 开发指南

- `README.md` - Agent Runtime 概述
- `docs/` - 详细的 Agent 文档

### 6. 测试文档
**位置**: `apps/api/tests/`  
**用途**: 测试脚本和测试说明

- `test_workflow_simple.py` - 简单的工作流验证
- `test_full_workflow.py` - 完整的端到端测试
- `README.md` - 测试说明

---

## 🔍 如何找到你需要的文档

### 我想了解...

| 需求 | 文档位置 |
|------|---------|
| 项目是什么 | `README.md` |
| 项目完成了什么 | `PROJECT_SUMMARY.md` |
| 系统怎么设计的 | `docs/engineering/SYSTEM-BLUEPRINT.md` |
| 开发计划是什么 | `docs/engineering/DELIVERY-PLAN.md` |
| 现在应该做什么 | `docs/engineering/ITERATION2_NEXT_STEPS.md` |
| 如何运行项目 | `apps/api/QUICKSTART.md` |
| 遇到问题怎么办 | `apps/api/TROUBLESHOOTING.md` |
| 如何运行测试 | `apps/api/E2E_TEST_GUIDE.md` |
| 某个功能的需求 | `.kiro/specs/<功能名>/requirements.md` |
| 某个功能的设计 | `.kiro/specs/<功能名>/design.md` |
| 某个功能的任务 | `.kiro/specs/<功能名>/tasks.md` |
| 如何开发 Agent | `workers/agent-runtime/README.md` |

---

## 📝 文档命名规范

### 文件命名
- 使用大写字母和下划线：`SYSTEM_BLUEPRINT.md`
- 或使用小写字母和连字符：`quick-start.md`
- 保持一致性

### 目录命名
- 使用小写字母和连字符：`text-pipeline-mock/`
- 简洁明了，见名知意

### 特殊文档
- `README.md` - 目录索引或模块说明
- `CHANGELOG.md` - 变更日志
- `CONTRIBUTING.md` - 贡献指南

---

## 🔄 文档更新流程

### 何时更新文档

1. **完成一个迭代** → 更新 `ITERATION*_NEXT_STEPS.md`
2. **架构变更** → 更新 `SYSTEM-BLUEPRINT.md`
3. **计划调整** → 更新 `DELIVERY-PLAN.md`
4. **新功能开发** → 创建新的 Spec 目录
5. **API 变更** → 更新 API 文档

### 文档审查清单

- [ ] 文档放在正确的位置
- [ ] 文档命名符合规范
- [ ] 相关文档的链接已更新
- [ ] 索引文档已更新
- [ ] 日期和版本信息正确

---

## 📊 当前文档状态

### 已完成的文档
- ✅ 项目 README
- ✅ 项目总结
- ✅ 系统架构蓝图
- ✅ 交付计划
- ✅ Iteration 2 总结
- ✅ 工程文档索引
- ✅ 文本主链路 Spec（需求、设计、任务）
- ✅ 代码重构 Spec
- ✅ API 快速开始指南
- ✅ 故障排查指南
- ✅ 端到端测试指南

### 待创建的文档
- ⏳ API 契约文档（API-CONTRACT.md）
- ⏳ 工作流契约文档（WORKFLOW-CONTRACT.md）
- ⏳ Agent 契约文档（AGENT-CONTRACT.md）
- ⏳ 产品规格文档（docs/product/）
- ⏳ 设计系统文档（docs/design/）

---

## 🎯 文档组织原则

1. **按用途分类** - 工程、产品、设计分开
2. **按层级组织** - 项目级 → 模块级 → 功能级
3. **保持简洁** - 避免文档散落各处
4. **便于查找** - 提供清晰的索引和导航
5. **及时更新** - 文档与代码同步更新

---

**最后更新**: 2026-04-07  
**维护者**: 项目团队
