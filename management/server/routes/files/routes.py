from flask import jsonify, request, send_file, current_app
from io import BytesIO
from .. import files_bp


from services.files.service import (
    get_files_list, 
    get_file_info, 
    download_file_from_minio, 
    delete_file, 
    batch_delete_files, 
    upload_files_to_server,
    create_folder,
    get_folder_tree
)
from services.files.utils import FileType

UPLOAD_FOLDER = "/data/uploads"
ALLOWED_EXTENSIONS = {"txt", "pdf", "png", "jpg", "jpeg", "gif", "doc", "docx", "xls", "xlsx"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@files_bp.route("/create_folder", methods=["POST"])
def create_folder_route():
    """
    创建文件夹API
    
    请求参数:
    - parent_id: 父文件夹ID (可选，为空则在根目录创建)
    - folder_name: 文件夹名称 (必需)
    - user_id: 用户ID (可选)
    
    返回:
    - code: 状态码 (0表示成功)
    - data: 创建的文件夹信息
    - message: 消息
    """
    try:
        data = request.get_json()
        
        if not data or 'folder_name' not in data:
            return jsonify({
                'code': 1,
                'message': '缺少必需参数: folder_name'
            }), 400
        
        parent_id = data.get('parent_id')
        folder_name = data.get('folder_name')
        user_id = data.get('user_id')
        
        # 验证文件夹名称
        if not folder_name or not folder_name.strip():
            return jsonify({
                'code': 1,
                'message': '文件夹名称不能为空'
            }), 400
        
        # 创建文件夹
        folder = create_folder(parent_id, folder_name.strip(), user_id)
        
        return jsonify({
            'code': 0,
            'data': folder,
            'message': '文件夹创建成功'
        })
        
    except Exception as e:
        current_app.logger.error(f"创建文件夹API错误: {str(e)}")
        return jsonify({
            'code': 1,
            'message': f'创建文件夹失败: {str(e)}'
        }), 500


@files_bp.route("/folder_tree", methods=["GET"])
def get_folder_tree_route():
    """
    获取文件夹树API
    
    请求参数:
    - parent_id: 父文件夹ID (可选，为空则从根目录开始)
    - user_id: 用户ID (可选)
    
    返回:
    - code: 状态码 (0表示成功)
    - data: 文件夹树结构
    - message: 消息
    """
    try:
        parent_id = request.args.get('parent_id')
        user_id = request.args.get('user_id')
        
        # 获取文件夹树
        tree = get_folder_tree(parent_id, user_id)
        
        return jsonify({
            'code': 0,
            'data': tree,
            'message': '获取文件夹树成功'
        })
        
    except Exception as e:
        current_app.logger.error(f"获取文件夹树API错误: {str(e)}")
        return jsonify({
            'code': 1,
            'message': f'获取文件夹树失败: {str(e)}'
        }), 500


@files_bp.route("/upload", methods=["POST"])
def upload_file():
    if "files" not in request.files:
        current_app.logger.error("未选择文件")
        return jsonify({"code": 400, "message": "未选择文件", "data": None}), 400

    files = request.files.getlist("files")
    current_app.logger.info(f"接收到上传请求，文件数量: {len(files)}")
    
    # 获取目标文件夹ID和用户ID
    parent_id = request.form.get('parent_id')
    user_id = request.form.get('user_id')
    
    try:
        upload_result = upload_files_to_server(files, parent_id, user_id)
        current_app.logger.info(f"上传结果: {upload_result}")
        return jsonify({"code": 0, "message": "上传成功", "data": upload_result["data"]})
    except Exception as e:
        current_app.logger.error(f"上传文件失败: {str(e)}")
        return jsonify({"code": 500, "message": f"上传文件失败: {str(e)}", "data": None}), 500


@files_bp.route("", methods=["GET", "OPTIONS"])
def get_files():
    """获取文件列表的API端点"""
    if request.method == "OPTIONS":
        return "", 200

    try:
        current_page = int(request.args.get("currentPage", 1))
        page_size = int(request.args.get("size", 10))
        name_filter = request.args.get("name", "")
        sort_by = request.args.get("sort_by", "create_time")
        sort_order = request.args.get("sort_order", "desc")
        parent_id = request.args.get("parent_id")

        result, total = get_files_list(current_page, page_size, name_filter, sort_by, sort_order, parent_id)

        return jsonify({"code": 0, "data": {"list": result, "total": total}, "message": "获取文件列表成功"})

    except Exception as e:
        return jsonify({"code": 500, "message": f"获取文件列表失败: {str(e)}"}), 500


@files_bp.route("/<string:file_id>/download", methods=["GET", "OPTIONS"])
def download_file(file_id):
    try:
        current_app.logger.info(f"开始处理文件下载请求: {file_id}")

        # 获取文件信息
        file = get_file_info(file_id)

        if not file:
            current_app.logger.error(f"文件不存在: {file_id}")
            return jsonify({"code": 404, "message": f"文件 {file_id} 不存在", "details": "文件记录不存在或已被删除"}), 404

        if file["type"] == FileType.FOLDER.value:
            current_app.logger.error(f"不能下载文件夹: {file_id}")
            return jsonify({"code": 400, "message": "不能下载文件夹", "details": "请选择一个文件进行下载"}), 400

        current_app.logger.info(f"文件信息获取成功: {file_id}, 存储位置: {file['parent_id']}/{file['location']}")

        try:
            # 从MinIO下载文件
            file_data, filename = download_file_from_minio(file_id)

            # 创建内存文件对象
            file_stream = BytesIO(file_data)

            # 返回文件
            return send_file(file_stream, download_name=filename, as_attachment=True, mimetype="application/octet-stream")

        except Exception as e:
            current_app.logger.error(f"下载文件失败: {str(e)}")
            return jsonify({"code": 500, "message": "下载文件失败", "details": str(e)}), 500

    except Exception as e:
        current_app.logger.error(f"处理下载请求时出错: {str(e)}")
        return jsonify({"code": 500, "message": "处理下载请求时出错", "details": str(e)}), 500


@files_bp.route("/<string:file_id>", methods=["DELETE", "OPTIONS"])
def delete_file_route(file_id):
    """删除文件的API端点"""
    if request.method == "OPTIONS":
        return "", 200

    try:
        success = delete_file(file_id)

        if success:
            return jsonify({"code": 0, "message": "文件删除成功"})
        else:
            return jsonify({"code": 404, "message": f"文件 {file_id} 不存在"}), 404

    except Exception as e:
        return jsonify({"code": 500, "message": f"删除文件失败: {str(e)}"}), 500


@files_bp.route("/batch", methods=["DELETE", "OPTIONS"])
def batch_delete_files_route():
    """批量删除文件的API端点"""
    if request.method == "OPTIONS":
        return "", 200

    try:
        data = request.json
        file_ids = data.get("ids", [])

        if not file_ids:
            return jsonify({"code": 400, "message": "未提供要删除的文件ID"}), 400

        success_count = batch_delete_files(file_ids)

        return jsonify({"code": 0, "message": f"成功删除 {success_count}/{len(file_ids)} 个文件"})

    except Exception as e:
        return jsonify({"code": 500, "message": f"批量删除文件失败: {str(e)}"}), 500
