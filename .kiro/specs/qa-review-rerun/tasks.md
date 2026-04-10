# Iteration 5: QA / Review / Rerun 闭环 - 实现计划

## 概述

本迭代的目标是实现完整的质量保证和迭代优化闭环。通过 QA Runtime、Review Gate 和 Rerun 功能，让系统从"能生成"升级为"能返工、能审核、能放行"。

---

## 任务列表

- [x] 1. QA Runtime 基础框架




  - [x] 1.1 创建 QA Runtime 类


    - 创建 QARuntime 类
    - 实现 execute_qa 方法
    - 集成 QARepository
    - _需求: 1.1, 1.2, 1.3_

  - [x] 1.2 实现 QA 报告生成


    - 创建 QAReport 记录
    - 记录检查结果到 issues_jsonb
    - 计算 score 和 severity
    - _需求: 1.2, 1.3_

  - [x] 1.3 集成 QA Stage 到 Workflow


    - 在 workflow 中添加 qa Stage
    - 在 media chain 完成后执行 QA
    - 根据 QA 结果决定是否继续
    - _需求: 1.4, 1.5_

  - [ ]* 1.4 编写 QA Runtime 单元测试
    - 测试 QA 报告生成
    - 测试结果记录
    - 测试错误处理
    - _需求: 1.1, 1.2, 1.3_

- [x] 2. 规则检查实现





  - [x] 2.1 实现 Brief 规则检查


    - 检查必填字段
    - 检查字段格式
    - 生成问题列表
    - _需求: 2.1_

  - [x] 2.2 实现 Character 规则检查

    - 检查角色数量
    - 检查角色字段完整性
    - 检查 visual_anchors
    - _需求: 2.2_

  - [x] 2.3 实现 Script 规则检查

    - 检查场景结构
    - 检查对白格式
    - 检查时长合理性
    - _需求: 2.3_

  - [x] 2.4 实现 Storyboard 规则检查

    - 检查 Shot 数量
    - 检查总时长
    - 检查 Shot 结构
    - _需求: 2.4_

  - [ ]* 2.5 编写规则检查单元测试
    - 测试各类规则检查
    - 测试问题记录
    - 测试边界情况
    - _需求: 2.1, 2.2, 2.3, 2.4, 2.5_


- [x] 3. 语义一致性检查





  - [x] 3.1 实现角色一致性检查


    - 比较 Character Profile 和 Script 中的角色
    - 检查角色描述一致性
    - 生成不一致问题
    - _需求: 3.1_

  - [x] 3.2 实现世界观一致性检查

    - 加载 Story Bible 设定
    - 检查 Script 是否违反设定
    - 生成违反问题
    - _需求: 3.2_

  - [x] 3.3 实现情节连贯性检查

    - 检查场景转换合理性
    - 检查时间线连贯性
    - 生成连贯性问题
    - _需求: 3.3_

  - [ ]* 3.4 编写语义检查单元测试
    - 测试角色一致性检查
    - 测试世界观检查
    - 测试情节检查
    - _需求: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 4. Review Gate 实现




  - [x] 4.1 创建 Review Gate Service


    - 创建 ReviewGateService 类
    - 实现 pause_for_review 方法
    - 实现 submit_review 方法
    - 实现 process_decision 方法
    - _需求: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [x] 4.2 实现 Workflow 暂停逻辑


    - 检查 Stage 的 review_required 标志
    - 更新 StageTask review_status
    - 暂停 workflow 执行
    - _需求: 5.1, 5.2_

  - [x] 4.3 实现审核决策处理


    - 创建 ReviewDecision 记录
    - 根据 decision 更新 workflow 状态
    - approved: 恢复执行
    - rejected: 终止 workflow
    - revision_required: 触发 rerun
    - _需求: 5.4, 5.5, 6.1, 6.2, 6.3, 6.4, 6.5_

  - [ ]* 4.4 编写 Review Gate 单元测试
    - 测试 workflow 暂停
    - 测试审核决策处理
    - 测试 workflow 恢复
    - _需求: 5.1, 5.2, 5.3, 5.4, 5.5_


- [ ] 5. Workflow Rerun 功能
  - [ ] 5.1 创建 Rerun Service
    - 创建 RerunService 类
    - 实现 rerun_workflow 方法
    - 实现 get_rerun_history 方法
    - _需求: 7.1, 7.2, 7.3, 7.4, 7.5_

  - [ ] 5.2 实现 Rerun WorkflowRun 创建
    - 创建新 WorkflowRun
    - 设置 rerun_from_stage 字段
    - 设置 parent_workflow_run_id
    - 记录 rerun_reason
    - _需求: 7.1, 7.2_

  - [ ] 5.3 实现 Rerun 执行逻辑
    - 从 rerun_from_stage 开始执行
    - 执行所有后续 Stage
    - 保留之前 Stage 的产物
    - 生成新版本产物
    - _需求: 7.3, 7.4, 9.1, 9.2_

  - [ ] 5.4 实现数据保护机制
    - 使用数据库事务
    - 失败时回滚更改
    - 不覆盖现有数据
    - 保留历史版本
    - _需求: 7.5, 9.3, 9.5_

  - [ ]* 5.5 编写 Rerun Service 单元测试
    - 测试 rerun 创建
    - 测试 rerun 执行
    - 测试数据隔离
    - 测试失败处理
    - _需求: 7.1, 7.2, 7.3, 7.4, 7.5_

- [ ] 6. Shot 级别 Rerun
  - [ ] 6.1 实现 Shot Rerun 方法
    - 实现 rerun_shots 方法
    - 接收 shot_ids 参数
    - 创建 rerun WorkflowRun
    - _需求: 8.1, 8.2_

  - [ ] 6.2 实现 Shot 过滤逻辑
    - 只处理指定的 Shot
    - 跳过其他 Shot
    - 保留其他 Shot 的 Asset
    - _需求: 8.2, 8.3_

  - [ ] 6.3 实现批量 Shot Rerun
    - 支持多个 Shot 同时 rerun
    - 并行处理 Shot
    - 聚合结果
    - _需求: 8.5_

  - [ ]* 6.4 编写 Shot Rerun 单元测试
    - 测试单个 Shot rerun
    - 测试批量 rerun
    - 测试数据隔离
    - _需求: 8.1, 8.2, 8.3, 8.4, 8.5_


- [ ] 7. QA 报告 API
  - [ ] 7.1 创建 QA 报告查询端点
    - GET /episodes/{episode_id}/qa-reports
    - 返回所有 QA 报告
    - 按时间倒序排列
    - _需求: 10.1, 10.5_

  - [ ] 7.2 创建 QA 报告详情端点
    - GET /qa-reports/{report_id}
    - 返回报告详情
    - 包含所有 issues
    - _需求: 10.2, 10.3_

  - [ ] 7.3 实现 QA 报告 Schema
    - 定义 QAReportResponse
    - 定义 IssueDetail
    - 定义 QAReportList
    - _需求: 10.1, 10.2, 10.3_

- [ ] 8. Review API
  - [ ] 8.1 创建审核提交端点
    - POST /stage-tasks/{stage_task_id}/review
    - 接收 decision 和 comment
    - 创建 ReviewDecision
    - _需求: 11.3, 6.1, 6.2_

  - [ ] 8.2 创建审核历史查询端点
    - GET /episodes/{episode_id}/reviews
    - 返回所有审核记录
    - 按时间倒序排列
    - _需求: 12.1, 12.2_

  - [ ] 8.3 实现 Review Schema
    - 定义 ReviewSubmitRequest
    - 定义 ReviewDecisionResponse
    - 定义 ReviewHistoryResponse
    - _需求: 11.3, 6.1_

- [ ] 9. Rerun API
  - [ ] 9.1 创建 Workflow Rerun 端点
    - POST /episodes/{episode_id}/rerun
    - 接收 from_stage 参数
    - 创建 rerun WorkflowRun
    - _需求: 7.1, 7.2_

  - [ ] 9.2 创建 Shot Rerun 端点
    - POST /episodes/{episode_id}/rerun-shots
    - 接收 shot_ids 和 stage_type
    - 创建 Shot rerun WorkflowRun
    - _需求: 8.1, 8.2_

  - [ ] 9.3 创建 Rerun 历史查询端点
    - GET /episodes/{episode_id}/rerun-history
    - 返回所有 rerun 记录
    - 标识 rerun 类型
    - _需求: 12.1, 12.2, 12.3_

  - [ ] 9.4 实现 Rerun Schema
    - 定义 RerunWorkflowRequest
    - 定义 RerunShotsRequest
    - 定义 RerunHistoryResponse
    - _需求: 7.1, 8.1, 12.1_


- [ ] 10. Workspace 集成
  - [ ] 10.1 更新 Workspace 聚合逻辑
    - 包含 QA 报告摘要
    - 包含 Review 状态
    - 包含 Rerun 历史
    - _需求: 11.1, 15.1_

  - [ ] 10.2 更新 Workspace Schema
    - 添加 qa_summary 字段
    - 添加 review_status 字段
    - 添加 rerun_count 字段
    - _需求: 11.1, 15.1_

  - [ ] 10.3 实现 QA 失败提示
    - 在 Workspace 显示 QA 失败
    - 高亮 critical 问题
    - 提供查看详情入口
    - _需求: 10.4, 11.1_

  - [ ]* 10.4 编写 Workspace 集成测试
    - 测试 QA 信息展示
    - 测试 Review 状态展示
    - 测试 Rerun 历史展示
    - _需求: 11.1, 15.1_

- [ ] 11. 数据库 Migration
  - [ ] 11.1 扩展 WorkflowRun 表
    - 添加 parent_workflow_run_id 字段
    - 添加 rerun_reason 字段
    - 添加 rerun_shot_ids_jsonb 字段
    - _需求: 7.1, 7.2, 8.1_

  - [ ] 11.2 创建索引
    - qa_reports: (episode_id, created_at DESC)
    - review_decisions: (stage_task_id, created_at DESC)
    - workflow_runs: (episode_id, rerun_from_stage)
    - _需求: 10.5, 12.1, 15.4_

  - [ ] 11.3 编写 Migration 脚本
    - 创建 006_qa_review_rerun.sql
    - 测试 migration
    - 更新 README
    - _需求: 所有_

- [ ] 12. 文档和示例
  - [ ] 12.1 编写 QA Runtime 使用文档
    - 记录 QA 检查类型
    - 提供配置示例
    - 说明扩展方法
    - _需求: 1.1, 2.1, 3.1_

  - [ ] 12.2 编写 Review 流程文档
    - 说明审核流程
    - 提供决策示例
    - 说明 rerun 触发
    - _需求: 5.1, 6.1, 11.1_

  - [ ] 12.3 编写 Rerun 使用指南
    - 说明 rerun 类型
    - 提供使用示例
    - 说明注意事项
    - _需求: 7.1, 8.1, 9.1_

  - [ ] 12.4 编写 Iteration 5 完成报告
    - 总结完成的任务
    - 记录关键指标
    - 列出已知问题
    - 提供下一步建议
    - _需求: 所有_


- [ ] 13. Checkpoint - 确保核心功能可用
  - 运行端到端测试
  - 验证 QA 检查
  - 验证 Review 流程
  - 验证 Rerun 功能
  - 确认所有核心功能可用，询问用户是否有问题

---

## 任务优先级

### 高优先级（必须完成）

1. 任务 1: QA Runtime 基础框架
2. 任务 2: 规则检查实现
3. 任务 4: Review Gate 实现
4. 任务 5: Workflow Rerun 功能
5. 任务 7: QA 报告 API
6. 任务 8: Review API
7. 任务 9: Rerun API

### 中优先级（尽量完成）

1. 任务 3: 语义一致性检查
2. 任务 6: Shot 级别 Rerun
3. 任务 10: Workspace 集成
4. 任务 11: 数据库 Migration

### 低优先级（可推迟）

1. 任务 12: 文档和示例
2. 媒体资产质量检查（可推迟到 Iteration 6）

---

## 验收标准（DoD）

本迭代完成的标准：

1. ✅ QA Runtime 可以执行规则检查和语义检查
2. ✅ QA 失败会阻止 final export
3. ✅ Review Gate 可以暂停 workflow 等待审核
4. ✅ 审核决策可以恢复或终止 workflow
5. ✅ Workflow Rerun 可以从指定 Stage 重新执行
6. ✅ Shot 级别 Rerun 可以只重跑指定 Shot
7. ✅ Rerun 不覆盖非目标对象
8. ✅ 用户能看懂为什么被打回
9. ✅ 至少一个完整的 QA/Review/Rerun 流程可以走通

---

## 风险和注意事项

### QA 检查性能风险

**风险**: QA 检查可能耗时过长

**缓解措施**:
- 设置 30 秒超时
- 优化检查算法
- 支持异步执行
- 提供进度反馈

### Rerun 数据一致性风险

**风险**: Rerun 可能破坏数据一致性

**缓解措施**:
- 使用数据库事务
- 失败时回滚
- 保留历史版本
- 详细测试

### Review 流程复杂性风险

**风险**: Review 流程可能过于复杂

**缓解措施**:
- 简化决策选项
- 提供清晰指引
- 记录详细日志
- 支持撤销操作

### 语义检查准确性风险

**风险**: 语义检查可能产生误报

**缓解措施**:
- 设置合理阈值
- 提供人工确认
- 持续优化算法
- 收集用户反馈

---

## 相关文档

- **需求文档**: `.kiro/specs/qa-review-rerun/requirements.md`
- **设计文档**: `.kiro/specs/qa-review-rerun/design.md`
- **项目总体任务**: `.kiro/specs/project-overview/tasks.md`
- **Iteration 4 完成报告**: `.kiro/specs/media-pipeline-alpha/ITERATION4_COMPLETION_REPORT.md`
- **系统蓝图**: `docs/engineering/SYSTEM-BLUEPRINT.md`
- **交付计划**: `docs/engineering/DELIVERY-PLAN.md`

---

**创建日期**: 2026-04-10  
**预计完成**: 第 9-10 周  
**当前状态**: 准备开始

