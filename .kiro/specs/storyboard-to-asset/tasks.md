# Iteration 3: Storyboard 到 Asset 工作台 - 实现计划

## 概述

本迭代的目标是验证和完善 Shot 结构，确保 Storyboard 可以稳定驱动后续的媒体链路。重点是数据完整性验证、输入构建逻辑设计，以及为 Iteration 4 做好准备。

---

## 任务列表

- [x] 1. 验证 Shot 模型和数据完整性




  - [x] 1.1 创建 Shot 数据完整性验证脚本


    - 编写 Python 脚本检查 Shot 表结构
    - 验证所有必需字段存在
    - 检查字段类型和约束
    - 输出验证报告
    - _需求: 1.1, 1.2, 1.3, 1.4, 1.5, 11.1_

  - [x] 1.2 验证 visual_constraints_jsonb 结构

    - 定义 visual_constraints 的 JSON Schema
    - 编写验证函数检查 Schema 符合性
    - 测试现有 Shot 记录的 visual_constraints
    - 记录不符合 Schema 的记录
    - _需求: 2.1, 2.2, 2.3, 2.4, 11.2_

  - [x] 1.3 验证 Shot 与 visual_spec 的一致性

    - 查询 Episode 的 visual_spec 文档和 Shot 记录
    - 比较 shot_count 与实际 Shot 数量
    - 比较 visual_spec.shots 与 Shot.visual_constraints
    - 生成一致性报告
    - _需求: 3.5, 4.1, 4.2, 11.3_

  - [x] 1.4 验证 character_refs 引用有效性

    - 加载 Episode 的 character_profile 文档
    - 提取所有角色名称
    - 检查 Shot.character_refs 中的角色是否存在
    - 生成引用错误报告
    - _需求: 2.5, 11.4_

  - [ ]* 1.5 编写 Shot 验证单元测试
    - 测试必需字段检查
    - 测试 visual_constraints Schema 验证
    - 测试一致性检查
    - 测试引用验证
    - _需求: 1.1, 2.1, 3.5, 2.5_

- [x] 2. 实现 ShotValidationService




  - [x] 2.1 创建 ShotValidationService 类


    - 定义 ValidationResult、ValidationError、ValidationWarning 数据类
    - 实现 validate_shot_completeness 方法
    - 实现 validate_visual_constraints_schema 方法
    - 实现 validate_shot_visual_spec_consistency 方法
    - _需求: 1.1, 2.1, 3.5, 4.2_

  - [x] 2.2 集成到 Storyboard Agent


    - 在 Storyboard Agent 的 validator_stage 中调用 ShotValidationService
    - 处理验证错误和警告
    - 记录验证结果到日志
    - _需求: 1.1, 2.1_

  - [ ]* 2.3 编写 ShotValidationService 单元测试
    - 测试各个验证方法
    - 测试错误和警告生成
    - 测试边界情况
    - _需求: 1.1, 2.1, 3.5_

- [x] 3. 设计和实现 ImageRenderInputBuilder




  - [x] 3.1 定义 ImageRenderInput 数据类


    - 定义所有必需字段
    - 添加字段验证
    - 添加序列化方法
    - _需求: 5.1, 5.2, 5.3, 5.4_

  - [x] 3.2 实现 ImageRenderInputBuilder 类

    - 实现 build_input_for_shot 方法
    - 实现 build_inputs_for_episode 方法
    - 实现 _merge_prompt_with_anchors 私有方法
    - 实现 _load_character_profile 私有方法
    - _需求: 5.1, 5.2, 5.3, 5.4, 5.5, 12.1, 12.2, 12.3, 12.4, 12.5_

  - [x] 3.3 实现 render_prompt 与 visual_anchor 合并逻辑

    - 提取 character_refs 中每个角色的 visual_anchor
    - 检查 render_prompt 是否已包含 visual_anchor 关键词
    - 智能插入 visual_anchor 到 render_prompt
    - 避免重复和冗余
    - _需求: 5.2, 12.3_

  - [ ]* 3.4 编写 ImageRenderInputBuilder 单元测试
    - 测试单个 Shot 输入构建
    - 测试批量输入构建
    - 测试 visual_anchor 合并逻辑
    - 测试缺失数据处理
    - _需求: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [ ]* 3.5 编写 ImageRenderInputBuilder 集成测试
    - 创建完整的测试数据（Episode、character_profile、visual_spec、Shot）
    - 调用 ImageRenderInputBuilder
    - 验证输入参数完整性和正确性
    - _需求: 5.1, 5.2, 5.3, 5.4_

- [x] 4. 完善 Shot Repository 和 API





  - [x] 4.1 验证 Shot Repository 功能


    - 测试 Shot 创建和查询
    - 测试版本控制
    - 测试按 scene_no 和 shot_no 排序
    - 测试批量查询
    - _需求: 1.1, 4.1, 4.5_

  - [x] 4.2 创建 Shot 查询 API 端点


    - GET /episodes/{episode_id}/shots - 查询 Episode 的所有 Shot
    - GET /shots/{shot_id} - 查询单个 Shot 详情
    - 支持版本参数查询历史版本
    - 返回包含 visual_constraints 的完整信息
    - _需求: 6.1, 9.1, 9.2, 9.3, 9.4, 9.5_

  - [x] 4.3 创建 Shot 编辑 API 端点（可选）


    - PUT /shots/{shot_id} - 更新 Shot 的 visual_constraints
    - 创建新版本而不是覆盖
    - 验证 visual_constraints Schema
    - 记录编辑来源
    - _需求: 7.1, 7.2, 7.5_

  - [ ]* 4.4 编写 Shot API 端点测试
    - 测试查询端点
    - 测试编辑端点
    - 测试版本控制
    - 测试错误处理
    - _需求: 6.1, 7.1, 7.2, 9.1_

- [x] 5. 更新 Workspace 聚合逻辑





  - [x] 5.1 在 Workspace 响应中包含 Shot 详情


    - 查询 Episode 的所有 Shot（最新版本）
    - 包含 visual_constraints 摘要
    - 按 scene_no 和 shot_no 排序
    - _需求: 9.1, 9.2, 9.5_

  - [x] 5.2 在 Workspace 响应中包含 visual_spec 引用


    - 查询 Episode 的最新 visual_spec 文档
    - 在 Shot 信息中包含 visual_spec 文档 ID
    - _需求: 9.3_

  - [x] 5.3 优化 Workspace 查询性能


    - 使用连接查询减少数据库往返
    - 批量加载 Shot 和文档
    - 添加适当的索引
    - _需求: 9.1_

  - [ ]* 5.4 编写 Workspace 聚合测试
    - 测试 Shot 信息包含
    - 测试排序正确性
    - 测试性能
    - _需求: 9.1, 9.2, 9.5_

- [x] 6. 准备资产管理基础





  - [x] 6.1 验证 Asset 表结构


    - 检查 shot_id 外键约束
    - 检查 asset_type 字段
    - 检查 is_selected 字段
    - 验证索引存在
    - _需求: 8.1, 8.2, 8.3_

  - [x] 6.2 创建 Asset Repository 基础方法


    - create_asset - 创建资产记录
    - get_assets_by_shot - 查询 Shot 的所有资产
    - get_selected_asset_by_shot - 查询 Shot 的主资产
    - update_selected_asset - 更新主资产标记
    - _需求: 8.1, 8.4, 8.5, 10.2, 10.3_

  - [x] 6.3 实现主资产选择逻辑


    - 确保同一 Shot 只有一个主资产
    - 更新 is_selected 字段
    - 记录选择操作
    - _需求: 10.2, 10.3, 10.4_

  - [ ]* 6.4 编写 Asset Repository 测试
    - 测试资产创建
    - 测试资产查询
    - 测试主资产选择
    - 测试唯一性约束
    - _需求: 8.1, 8.3, 10.2, 10.3_

- [x] 7. 文档和示例






  - [x] 7.1 编写 Shot 数据结构文档

    - 记录 Shot 模型的所有字段
    - 记录 visual_constraints 的 Schema
    - 提供示例数据
    - _需求: 1.1, 2.1_


  - [x] 7.2 编写 ImageRenderInput 使用文档

    - 记录 ImageRenderInput 的所有字段
    - 提供构建示例
    - 说明如何使用 ImageRenderInputBuilder
    - _需求: 5.1, 12.1_


  - [x] 7.3 编写 Iteration 3 完成报告

    - 总结完成的任务
    - 记录验证结果
    - 列出已知问题
    - 提供下一步建议
    - _需求: 所有_

- [x] 8. Checkpoint - 确保所有验证通过





  - 运行 Shot 数据完整性验证脚本
  - 运行所有单元测试
  - 运行集成测试
  - 确认所有验证通过，询问用户是否有问题

---

## 任务优先级

### 高优先级（必须完成）

1. 任务 1: 验证 Shot 模型和数据完整性
2. 任务 3: 设计和实现 ImageRenderInputBuilder
3. 任务 4.1: 验证 Shot Repository 功能
4. 任务 4.2: 创建 Shot 查询 API 端点

### 中优先级（尽量完成）

1. 任务 2: 实现 ShotValidationService
2. 任务 5: 更新 Workspace 聚合逻辑
3. 任务 6.1-6.2: 准备资产管理基础

### 低优先级（可推迟）

1. 任务 4.3: 创建 Shot 编辑 API 端点
2. 任务 6.3: 实现主资产选择逻辑
3. 任务 7: 文档和示例

---

## 验收标准（DoD）

本迭代完成的标准：

1. ✅ Shot 数据完整性验证脚本可运行并输出报告
2. ✅ visual_constraints Schema 验证通过
3. ✅ Shot 与 visual_spec 一致性验证通过
4. ✅ ImageRenderInputBuilder 可以为单个 Shot 构建输入
5. ✅ ImageRenderInputBuilder 可以为整个 Episode 批量构建输入
6. ✅ render_prompt 正确合并 visual_anchor
7. ✅ Shot 查询 API 端点可用
8. ✅ Workspace 返回完整的 Shot 信息
9. ✅ Asset Repository 基础方法实现
10. ✅ 所有核心功能的单元测试通过

---

## 风险和注意事项

### 数据一致性风险

**风险**: Shot 记录与 visual_spec 文档可能不一致

**缓解措施**:
- 在 Storyboard Agent 的 committer 阶段确保原子性
- 使用数据库事务保证一致性
- 实现验证脚本定期检查

### 性能风险

**风险**: 大量 Shot 时查询和构建输入可能较慢

**缓解措施**:
- 使用批量查询和连接查询
- 添加适当的数据库索引
- 实现分页查询

### 向后兼容性风险

**风险**: 修改 visual_constraints 结构可能影响现有数据

**缓解措施**:
- 使用 JSONB 类型保持灵活性
- 添加字段而不是修改现有字段
- 提供数据迁移脚本

---

## 相关文档

- **需求文档**: `.kiro/specs/storyboard-to-asset/requirements.md`
- **设计文档**: `.kiro/specs/storyboard-to-asset/design.md`
- **项目总体任务**: `.kiro/specs/project-overview/tasks.md`
- **Iteration 2 完成报告**: `.kiro/specs/text-pipeline-mock/ITERATION2_COMPLETION_REPORT.md`
- **交付计划**: `docs/engineering/DELIVERY-PLAN.md`
- **系统蓝图**: `docs/engineering/SYSTEM-BLUEPRINT.md`

---

**创建日期**: 2026-04-07  
**预计完成**: 第 5-6 周  
**当前状态**: 准备开始
