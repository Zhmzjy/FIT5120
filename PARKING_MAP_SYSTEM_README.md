# 墨尔本停车地图系统

## 概述

这是一个完整的墨尔本停车地图系统，集成了路边停车传感器和路外停车设施数据，提供实时的停车位可用性信息和交互式地图界面。

## 主要功能

### ✅ 已实现功能

1. **综合停车数据显示**
   - 显示所有 on-street（路边）和 off-street（路外）停车位
   - 实时传感器数据更新
   - 停车位状态高亮显示

2. **停车类型筛选**
   - 🅿️ **All Parking** - 显示所有停车位
   - 🚗 **On-Street** - 仅显示路边停车位
   - 🏢 **Off-Street** - 仅显示路外停车设施

3. **状态筛选**
   - **All Spaces** - 显示所有停车位
   - **Available Only** - 仅显示可用停车位
   - **Occupied Only** - 仅显示已占用停车位

4. **地图功能**
   - 交互式地图界面
   - 不同停车类型使用不同图标
   - 点击标记查看详细信息
   - 实时状态更新

5. **统计信息**
   - 总停车位数量
   - 路边停车位数量
   - 路外停车位数量
   - 占用率统计

## 技术架构

### 前端 (Vue.js 3)
- **框架**: Vue.js 3 + Composition API
- **地图**: Leaflet.js
- **样式**: 现代CSS + 响应式设计
- **构建工具**: Vite.js

### 后端 (Python Flask)
- **框架**: Flask + SQLAlchemy
- **数据库**: PostgreSQL
- **API**: RESTful API设计

### 数据库
- **on_street_sensors** - 路边停车传感器数据
- **off_street_parking** - 路外停车设施数据
- **suburbs** - 郊区边界数据

## 安装和设置

### 1. 环境要求
- Python 3.8+
- Node.js 16+
- PostgreSQL 12+

### 2. 后端设置

```bash
# 安装Python依赖
cd backend
pip install -r requirements.txt

# 设置环境变量
cp .env.example .env
# 编辑 .env 文件配置数据库连接

# 创建数据库表
cd ../database
psql -d your_database -f complete_schema.sql
psql -d your_database -f on_street_sensors_schema.sql
psql -d your_database -f parking_restrictions_schema.sql

# 导入数据
python import_on_street_sensors.py
python import_parking_restrictions.py

# 启动后端服务器
cd ../backend
python main.py
```

### 3. 前端设置

```bash
# 安装Node.js依赖
cd frontend
npm install

# 启动开发服务器
npm run dev
```

### 4. 访问应用

打开浏览器访问: `http://localhost:5173`

## API端点

### 综合停车数据
```
GET /api/parking/combined
```

**查询参数:**
- `parking_type`: 停车类型筛选 ('on-street', 'off-street', 'all')
- `status`: 状态筛选 ('available', 'occupied', 'all')
- `suburb`: 郊区名称筛选
- `zone`: 区域编号筛选
- `lat`, `lng`: 位置筛选
- `radius`: 搜索半径（公里）
- `limit`: 结果数量限制

### 统计信息
```
GET /api/stats
```

返回综合的停车统计信息，包括：
- 总停车位数量
- 路边停车位数量
- 路外停车位数量
- 占用率

### 传感器数据
```
GET /api/sensors/sensors
GET /api/sensors/sensors/geojson
GET /api/sensors/sensors/stats
```

### 停车设施数据
```
GET /api/parking/facilities
GET /api/parking/facilities/geojson
```

## 使用说明

### 地图界面

1. **停车类型筛选**
   - 点击顶部的停车类型按钮切换显示
   - 🅿️ All Parking: 显示所有停车位
   - 🚗 On-Street: 仅显示路边停车位
   - 🏢 Off-Street: 仅显示路外停车设施

2. **状态筛选**
   - 使用状态筛选按钮过滤停车位
   - Available Only: 仅显示可用停车位
   - Occupied Only: 仅显示已占用停车位

3. **地图交互**
   - 点击停车位标记查看详细信息
   - 使用地图控件进行缩放和平移
   - 点击"My Location"定位到当前位置

4. **搜索功能**
   - 在搜索框中输入郊区名称或邮政编码
   - 按回车键搜索相关停车位

### 数据更新

- 路边停车传感器数据实时更新
- 路外停车设施数据定期更新
- 统计信息自动刷新

## 数据源

### 路边停车传感器
- **来源**: 墨尔本政府开放数据
- **更新频率**: 实时
- **数据内容**: 传感器状态、位置、更新时间

### 路外停车设施
- **来源**: 墨尔本政府开放数据
- **更新频率**: 定期
- **数据内容**: 设施信息、停车位数量、位置

### 郊区边界
- **来源**: 墨尔本政府开放数据
- **用途**: 地理边界显示和筛选

## 性能优化

### 数据库优化
- 为常用查询字段创建索引
- 使用数据库视图优化复杂查询
- 实现数据分页加载

### 前端优化
- 使用虚拟滚动处理大量数据
- 实现地图标记聚合
- 缓存静态数据

### API优化
- 实现查询结果缓存
- 使用数据库连接池
- 优化查询语句

## 故障排除

### 常见问题

1. **地图不显示**
   - 检查网络连接
   - 确认Leaflet.js库已加载
   - 检查浏览器控制台错误

2. **数据不更新**
   - 检查后端服务器状态
   - 验证数据库连接
   - 查看API响应状态

3. **筛选功能不工作**
   - 检查前端JavaScript错误
   - 验证API参数格式
   - 确认数据库查询结果

### 调试模式

启用调试模式查看详细日志：

```bash
# 后端调试
export FLASK_ENV=development
python main.py

# 前端调试
npm run dev -- --debug
```

## 扩展功能

### 计划中的功能
- [ ] 用户位置导航
- [ ] 停车费用信息
- [ ] 历史数据图表
- [ ] 移动端应用
- [ ] 实时通知系统

### 自定义开发
- 添加新的数据源
- 实现自定义筛选条件
- 扩展地图功能
- 集成第三方服务

## 技术支持

如有问题或建议，请联系开发团队。

---

**版本**: 1.0.0  
**最后更新**: 2024年8月  
**维护者**: 墨尔本停车系统开发团队

