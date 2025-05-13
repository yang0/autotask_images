# Gitee图床插件

这个插件提供了基于Gitee仓库的图床服务，可以方便地上传图片并获取可访问的URL。


## 使用方法

### 1. 配置准备

1. 在Gitee上创建一个用于存储图片的仓库
2. 获取Gitee的访问令牌（Access Token）
3. 在系统中配置API密钥：
   - 提供者（provider）：`gitee.com`
   - 密钥名称（key_name）：`ACCESS_TOKEN`
   - 密钥值：你的Gitee访问令牌

### 2. 节点参数

#### 输入参数
- `image_path`：本地图片文件路径（支持文件选择器）
- `repo_url`：Gitee仓库地址

#### 输出参数
- `image_url`：上传后的图片URL地址

### 3. 使用示例

1. 在工作流中添加 `GiteeImageUploader` 节点
2. 设置仓库地址，例如：`gitee.com/username/images`
3. 选择要上传的图片文件
4. 运行节点后即可获得图片的访问地址

## 注意事项

1. 确保已正确配置Gitee访问令牌
2. 仓库必须具有写入权限
3. 建议使用专门的仓库存储图片
4. 图片会自动按日期归档，无需手动指定目录