<script lang="ts" setup>
import type { FormInstance, UploadUserFile } from "element-plus"
import { batchDeleteFilesApi, deleteFileApi, getFileListApi, uploadFileApi, createFolderApi, getFolderTreeApi } from "@@/apis/files"
import type { FolderData } from "@@/apis/files/type"
import { getTableDataApi } from "@@/apis/tables"
import { usePagination } from "@@/composables/usePagination"
import { Delete, Download, Refresh, Search, Upload, FolderAdd, Folder, ArrowLeft, Document, Picture } from "@element-plus/icons-vue"
import { ElLoading, ElMessage, ElMessageBox } from "element-plus"
import { reactive, ref, watch, onMounted, onActivated } from "vue"
import "element-plus/dist/index.css"
import "element-plus/theme-chalk/el-message-box.css"
import "element-plus/theme-chalk/el-message.css"

defineOptions({
  // 命名当前组件
  name: "File"
})

const loading = ref<boolean>(false)
const { paginationData, handleCurrentChange, handleSizeChange } = usePagination()
const uploadDialogVisible = ref(false)
const uploadFileList = ref<UploadUserFile[]>([])
const uploadLoading = ref(false)
const uploadProgress = ref(0)
const currentUploadingFile = ref("")
const uploadStatus = ref("")

// 创建文件夹相关
const createFolderDialogVisible = ref(false)
const createFolderForm = reactive({
  folder_name: "",
  parent_id: ""
})
const createFolderFormRef = ref<FormInstance | null>(null)
const createFolderLoading = ref(false)

// 文件夹树相关
const folderTreeDialogVisible = ref(false)
const folderTree = ref<FolderData[]>([])
const selectedFolderId = ref<string>("")
const selectedFolderName = ref<string>("根目录")

// 定义文件数据类型
interface FileData {
  id: string
  name: string
  size: number
  type: string
  kb_id: string
  location: string
  create_time?: number
  parent_id?: string
}

// 查询文件列表
const tableData = ref<FileData[]>([])
const searchFormRef = ref<FormInstance | null>(null)
const searchData = reactive({
  name: ""
})

// 当前目录相关
const currentFolderId = ref<string>("")
const currentFolderName = ref<string>("根目录")
const breadcrumbPath = ref<Array<{ id: string; name: string }>>([])

// 排序状态
const sortData = reactive({
  sortBy: "create_date",
  sortOrder: "desc" // 默认排序顺序 (最新创建的在前)
})

// 存储多选的表格数据
const multipleSelection = ref<FileData[]>([])

// 获取文件列表数据
function getTableData() {
  loading.value = true
  // 调用获取文件列表API
  getFileListApi({
    currentPage: paginationData.currentPage,
    size: paginationData.pageSize,
    name: searchData.name,
    sort_by: sortData.sortBy,
    sort_order: sortData.sortOrder,
    parent_id: currentFolderId.value || undefined
  }).then(({ data }) => {
    paginationData.total = data.total
    tableData.value = data.list
    // 清空选中数据
    multipleSelection.value = []
  }).catch(() => {
    tableData.value = []
  }).finally(() => {
    loading.value = false
  })
}

// 获取文件夹树
async function getFolderTree() {
  try {
    const response = await getFolderTreeApi()
    folderTree.value = response.data
  } catch (error) {
    ElMessage.error("获取文件夹树失败")
    folderTree.value = []
  }
}

// 搜索处理
function handleSearch() {
  paginationData.currentPage === 1 ? getTableData() : (paginationData.currentPage = 1)
}

// 重置搜索
function resetSearch() {
  searchFormRef.value?.resetFields()
  handleSearch()
}

// 进入文件夹
function enterFolder(folder: FileData) {
  if (folder.type !== 'folder') return
  
  currentFolderId.value = folder.id
  currentFolderName.value = folder.name
  
  // 自动将上传目录设置为当前目录
  selectedFolderId.value = folder.id
  selectedFolderName.value = folder.name
  
  // 更新面包屑导航
  breadcrumbPath.value.push({ id: folder.id, name: folder.name })
  
  // 重置分页并刷新数据
  paginationData.currentPage = 1
  getTableData()
}

// 返回上级目录
function goBack() {
  if (breadcrumbPath.value.length === 0) return
  
  breadcrumbPath.value.pop()
  
  if (breadcrumbPath.value.length === 0) {
    currentFolderId.value = ""
    currentFolderName.value = "根目录"
    // 自动将上传目录设置为根目录
    selectedFolderId.value = ""
    selectedFolderName.value = "根目录"
  } else {
    const parent = breadcrumbPath.value[breadcrumbPath.value.length - 1]
    currentFolderId.value = parent.id
    currentFolderName.value = parent.name
    // 自动将上传目录设置为当前目录
    selectedFolderId.value = parent.id
    selectedFolderName.value = parent.name
  }
  
  // 重置分页并刷新数据
  paginationData.currentPage = 1
  getTableData()
}

// 导航到指定目录
function navigateToFolder(folderId: string, folderName: string) {
  // 找到目标文件夹在面包屑中的位置
  const targetIndex = breadcrumbPath.value.findIndex(item => item.id === folderId)
  
  if (targetIndex >= 0) {
    // 截取面包屑到目标位置
    breadcrumbPath.value = breadcrumbPath.value.slice(0, targetIndex + 1)
  } else if (folderId === "") {
    // 返回根目录
    breadcrumbPath.value = []
  }
  
  currentFolderId.value = folderId
  currentFolderName.value = folderName
  
  // 自动将上传目录设置为当前目录
  selectedFolderId.value = folderId
  selectedFolderName.value = folderName
  
  // 重置分页并刷新数据
  paginationData.currentPage = 1
  getTableData()
}

// 获取文件图标
function getFileIcon(file: FileData) {
  if (file.type === 'folder') {
    return 'Folder'
  }
  
  const ext = file.name.split('.').pop()?.toLowerCase()
  switch (ext) {
    case 'pdf':
      return 'Document'
    case 'doc':
    case 'docx':
      return 'Document'
    case 'xls':
    case 'xlsx':
      return 'Document'
    case 'ppt':
    case 'pptx':
      return 'Document'
    case 'jpg':
    case 'jpeg':
    case 'png':
    case 'gif':
    case 'bmp':
      return 'Picture'
    case 'txt':
    case 'md':
      return 'Document'
    case 'html':
      return 'Document'
    default:
      return 'Document'
  }
}

// 修改创建文件夹函数，使用当前目录
function handleCreateFolder() {
  createFolderDialogVisible.value = true
  createFolderForm.folder_name = ""
  createFolderForm.parent_id = currentFolderId.value
}

// 修改选择上传目录，默认使用当前目录
function handleSelectUploadFolder() {
  folderTreeDialogVisible.value = true
  getFolderTree()
  // 如果当前在某个目录下，默认选择当前目录
  if (currentFolderId.value) {
    selectedFolderId.value = currentFolderId.value
    selectedFolderName.value = currentFolderName.value
  }
}

async function submitCreateFolder() {
  if (!createFolderFormRef.value) return
  
  const valid = await createFolderFormRef.value.validate()
  if (!valid) return
  
  createFolderLoading.value = true
  try {
    await createFolderApi({
      folder_name: createFolderForm.folder_name,
      parent_id: createFolderForm.parent_id || undefined
    })
    ElMessage.success("文件夹创建成功")
    createFolderDialogVisible.value = false
    getTableData()
    getFolderTree() // 刷新文件夹树
  } catch (error: unknown) {
    let errorMessage = "创建文件夹失败"
    if (error instanceof Error) {
      errorMessage += `: ${error.message}`
    }
    ElMessage.error(errorMessage)
  } finally {
    createFolderLoading.value = false
  }
}

// 选择文件夹
function selectFolder(folder: FolderData) {
  selectedFolderId.value = folder.id
  selectedFolderName.value = folder.name
  folderTreeDialogVisible.value = false
  ElMessage.success(`已选择目录: ${folder.name}`)
}

// 重置目录选择
function resetFolderSelection() {
  selectedFolderId.value = ""
  selectedFolderName.value = "根目录"
  ElMessage.success("已重置为根目录")
}

// 添加上传方法
function handleUpload() {
  uploadDialogVisible.value = true
}

async function submitUpload() {
  if (uploadFileList.value.length === 0) {
    ElMessage.warning("请选择要上传的文件")
    return
  }

  uploadLoading.value = true
  uploadProgress.value = 0
  uploadStatus.value = "准备上传..."
  
  const totalFiles = uploadFileList.value.length
  let successCount = 0
  let failCount = 0

  try {
    for (let i = 0; i < uploadFileList.value.length; i++) {
      const file = uploadFileList.value[i]
      if (!file.raw) continue

      currentUploadingFile.value = file.name
      uploadStatus.value = `正在上传 ${i + 1}/${totalFiles}: ${file.name}`
      uploadProgress.value = Math.round((i / totalFiles) * 100)

      const formData = new FormData()
      formData.append("files", file.raw)

      // 使用选择的上传目录，如果没有选择则使用当前目录
      const targetFolderId = selectedFolderId.value || currentFolderId.value || undefined
      if (targetFolderId) {
        formData.append("parent_id", targetFolderId)
      }

      try {
        await uploadFileApi(formData, targetFolderId)
        successCount++
      } catch (error) {
        console.error(`文件 ${file.name} 上传失败:`, error)
        failCount++
        ElMessage.error(`文件 ${file.name} 上传失败: ${error instanceof Error ? error.message : "未知错误"}`)
      }
    }

    // 更新最终进度
    uploadProgress.value = 100
    uploadStatus.value = `上传完成 (成功: ${successCount}, 失败: ${failCount})`

    if (successCount > 0) {
      ElMessage.success(`成功上传 ${successCount} 个文件${failCount > 0 ? `，${failCount} 个文件上传失败` : ""}`)
      getTableData()
      uploadDialogVisible.value = false
      uploadFileList.value = []
    } else {
      ElMessage.error("所有文件上传失败")
    }
  } catch (error) {
    ElMessage.error(`上传过程中发生错误: ${error instanceof Error ? error.message : "未知错误"}`)
  } finally {
    uploadLoading.value = false
    currentUploadingFile.value = ""
  }
}

// 下载文件
async function handleDownload(row: FileData) {
  const loadingInstance = ElLoading.service({
    lock: true,
    text: "正在准备下载...",
    background: "rgba(0, 0, 0, 0.7)"
  })

  try {
    console.log(`开始下载文件: ${row.id} ${row.name}`)

    // 直接使用fetch API进行文件下载
    const response = await fetch(`/api/v1/files/${row.id}/download`, {
      method: "GET",
      headers: {
        Accept: "application/octet-stream"
      }
    })

    if (!response.ok) {
      throw new Error(`服务器返回错误: ${response.status} ${response.statusText}`)
    }

    // 获取文件数据
    const blob = await response.blob()

    if (!blob || blob.size === 0) {
      throw new Error("文件内容为空")
    }

    // 创建下载链接
    const url = URL.createObjectURL(blob)
    const link = document.createElement("a")
    link.href = url
    link.download = row.name

    // 触发下载
    document.body.appendChild(link)
    link.click()

    // 清理资源
    setTimeout(() => {
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
      ElMessage.success(`文件 "${row.name}" 下载成功`)
    }, 100)
  } catch (error: any) {
    console.error("下载文件时发生错误:", error)
    ElMessage.error(`文件下载失败: ${error?.message || "未知错误"}`)
  } finally {
    loadingInstance.close()
  }
}

// 删除文件
function handleDelete(row: FileData) {
  ElMessageBox.confirm(
    `确定要删除文件 "${row.name}" 吗？`,
    "删除确认",
    {
      confirmButtonText: "确定",
      cancelButtonText: "取消",
      type: "warning",
      dangerouslyUseHTMLString: true,
      center: true,
      customClass: "delete-confirm-dialog",
      distinguishCancelAndClose: true,
      showClose: false,
      closeOnClickModal: false,
      closeOnPressEscape: true,
      roundButton: true,
      beforeClose: (action, instance, done) => {
        if (action === "confirm") {
          instance.confirmButtonLoading = true
          instance.confirmButtonText = "删除中..."

          loading.value = true
          deleteFileApi(row.id)
            .then(() => {
              ElMessage.success("删除成功")
              getTableData() // 刷新表格数据
              done()
            })
            .catch((error) => {
              ElMessage.error(`删除失败: ${error?.message || "未知错误"}`)
              done()
            })
            .finally(() => {
              instance.confirmButtonLoading = false
              loading.value = false
            })
        } else {
          done()
        }
      }
    }
  ).catch(() => {
    // 用户取消删除操作
  })
}

// 批量删除文件
function handleBatchDelete() {
  if (multipleSelection.value.length === 0) {
    ElMessage.warning("请至少选择一个文件")
    return
  }

  ElMessageBox.confirm(
    `确定要删除选中的 <strong>${multipleSelection.value.length}</strong> 个文件吗？<br><span style="color: #F56C6C; font-size: 12px;">此操作不可恢复</span>`,
    "批量删除确认",
    {
      confirmButtonText: "确定",
      cancelButtonText: "取消",
      type: "warning",
      dangerouslyUseHTMLString: true,
      center: true,
      customClass: "delete-confirm-dialog",
      distinguishCancelAndClose: true,
      showClose: false,
      closeOnClickModal: false,
      closeOnPressEscape: true,
      roundButton: true,
      beforeClose: (action, instance, done) => {
        if (action === "confirm") {
          instance.confirmButtonLoading = true
          instance.confirmButtonText = "删除中..."

          loading.value = true
          const ids = multipleSelection.value.map(item => item.id)
          batchDeleteFilesApi(ids)
            .then(() => {
              ElMessage.success(`成功删除 ${multipleSelection.value.length} 个文件`)
              getTableData() // 刷新表格数据
              done()
            })
            .catch((error) => {
              ElMessage.error(`批量删除失败: ${error?.message || "未知错误"}`)
              done()
            })
            .finally(() => {
              instance.confirmButtonLoading = false
              loading.value = false
            })
        } else {
          done()
        }
      }
    }
  ).catch(() => {
    // 用户取消删除操作
  })
}

// 表格多选事件处理
function handleSelectionChange(selection: FileData[]) {
  multipleSelection.value = selection
}

// 格式化文件大小
function formatFileSize(size: number) {
  if (size < 1024) {
    return `${size} B`
  } else if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(2)} KB`
  } else if (size < 1024 * 1024 * 1024) {
    return `${(size / (1024 * 1024)).toFixed(2)} MB`
  } else {
    return `${(size / (1024 * 1024 * 1024)).toFixed(2)} GB`
  }
}

/**
 * @description 处理表格排序变化事件（只允许正序和倒序切换）
 * @param {object} sortInfo 排序信息对象，包含 prop 和 order
 * @param {string} sortInfo.prop 排序的字段名
 * @param {string | null} sortInfo.order 排序的顺序 ('ascending', 'descending', null)
 */
function handleSortChange({ prop }: { prop: string, order: string | null }) {
  // 如果点击的是同一个字段，则切换排序顺序
  if (sortData.sortBy === prop) {
    // 当前为正序则切换为倒序，否则切换为正序
    sortData.sortOrder = sortData.sortOrder === "asc" ? "desc" : "asc"
  } else {
    // 切换字段时，默认正序
    sortData.sortBy = prop
    sortData.sortOrder = "asc"
  }
  getTableData()
}

// 监听分页参数的变化
watch([() => paginationData.currentPage, () => paginationData.pageSize], getTableData, { immediate: true })

// 确保页面挂载和激活时获取数据
onMounted(() => {
  // 初始化时确保上传目录和当前目录保持同步
  selectedFolderId.value = currentFolderId.value
  selectedFolderName.value = currentFolderName.value
  getTableData()
})

// 当从其他页面切换回来时刷新数据
onActivated(() => {
  getTableData()
})
</script>

<template>
  <div class="app-container">
    <el-card v-loading="loading" shadow="never" class="search-wrapper">
      <el-form ref="searchFormRef" :inline="true" :model="searchData">
        <el-form-item prop="name" label="文件名">
          <el-input v-model="searchData.name" placeholder="请输入" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">
            搜索
          </el-button>
          <el-button :icon="Refresh" @click="resetSearch">
            重置
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
    <el-card v-loading="loading" shadow="never">
      <!-- 面包屑导航 -->
      <div class="breadcrumb-wrapper">
        <el-breadcrumb separator="/">
          <el-breadcrumb-item>
            <el-button 
              type="primary" 
              text 
              @click="navigateToFolder('', '根目录')"
              :class="{ 'current-folder': currentFolderId === '' }"
            >
              根目录
            </el-button>
          </el-breadcrumb-item>
          <el-breadcrumb-item 
            v-for="(folder, index) in breadcrumbPath" 
            :key="folder.id"
          >
            <el-button 
              type="primary" 
              text 
              @click="navigateToFolder(folder.id, folder.name)"
              :class="{ 'current-folder': index === breadcrumbPath.length - 1 }"
            >
              {{ folder.name }}
            </el-button>
          </el-breadcrumb-item>
        </el-breadcrumb>
        <el-button 
          v-if="breadcrumbPath.length > 0"
          type="info" 
          :icon="ArrowLeft" 
          @click="goBack"
          size="small"
        >
          返回上级
        </el-button>
      </div>

      <div class="toolbar-wrapper">
        <div>
          <el-button
            type="success"
            :icon="FolderAdd"
            @click="handleCreateFolder"
          >
            新建文件夹
          </el-button>
          <el-button
            type="primary"
            :icon="Upload"
            @click="handleUpload"
          >
            上传文件
          </el-button>
          <el-button
            type="danger"
            :icon="Delete"
            :disabled="multipleSelection.length === 0"
            @click="handleBatchDelete"
          >
            批量删除
          </el-button>
        </div>
        <div class="folder-info">
          <span class="folder-label">当前目录：</span>
          <el-tag type="info" size="large">{{ currentFolderName }}</el-tag>
          <span class="folder-label">上传目录：</span>
          <el-tag type="success" size="large">{{ selectedFolderName }}</el-tag>
          <el-button
            type="info"
            :icon="Folder"
            size="small"
            @click="handleSelectUploadFolder"
          >
            选择目录
          </el-button>
          <el-button
            type="warning"
            size="small"
            @click="resetFolderSelection"
          >
            重置
          </el-button>
        </div>
      </div>

      <!-- 创建文件夹对话框 -->
      <el-dialog
        v-model="createFolderDialogVisible"
        title="新建文件夹"
        width="400px"
      >
        <el-form
          ref="createFolderFormRef"
          :model="createFolderForm"
          label-width="80px"
        >
          <el-form-item
            label="文件夹名"
            prop="folder_name"
            :rules="[
              { required: true, message: '请输入文件夹名称', trigger: 'blur' },
              { min: 1, max: 50, message: '长度在 1 到 50 个字符', trigger: 'blur' }
            ]"
          >
            <el-input
              v-model="createFolderForm.folder_name"
              placeholder="请输入文件夹名称"
              maxlength="50"
              show-word-limit
            />
          </el-form-item>
          <el-form-item label="父目录">
            <el-input
              :value="currentFolderName"
              readonly
              placeholder="根目录"
            />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="createFolderDialogVisible = false">
            取消
          </el-button>
          <el-button
            type="primary"
            :loading="createFolderLoading"
            @click="submitCreateFolder"
          >
            确认创建
          </el-button>
        </template>
      </el-dialog>

      <!-- 文件夹树选择对话框 -->
      <el-dialog
        v-model="folderTreeDialogVisible"
        title="选择上传目录"
        width="500px"
      >
        <div class="folder-tree-container">
          <div class="root-folder">
            <el-button
              type="primary"
              plain
              @click="selectFolder({ id: '', name: '根目录', parent_id: '', type: 'folder', size: 0, create_time: 0, create_date: '' })"
            >
              <el-icon><Folder /></el-icon>
              根目录
            </el-button>
          </div>
          <el-tree
            v-if="folderTree.length > 0"
            :data="folderTree"
            :props="{ children: 'children', label: 'name' }"
            node-key="id"
            class="folder-tree"
          >
            <template #default="{ node, data }">
              <div class="tree-node">
                <el-icon><Folder /></el-icon>
                <span class="node-label">{{ node.label }}</span>
                <el-button
                  type="primary"
                  size="small"
                  @click="selectFolder(data)"
                >
                  选择
                </el-button>
              </div>
            </template>
          </el-tree>
          <div v-else class="empty-tree">
            <el-empty description="暂无文件夹" />
          </div>
        </div>
      </el-dialog>

      <!-- 上传对话框 -->
      <el-dialog
        v-model="uploadDialogVisible"
        title="上传文件"
        width="500px"
      >
        <div class="upload-info">
          <p><strong>上传目录：</strong>{{ selectedFolderName }}</p>
        </div>
        <el-upload
          v-model:file-list="uploadFileList"
          multiple
          :auto-upload="false"
          drag
        >
          <el-icon class="el-icon--upload">
            <Upload />
          </el-icon>
          <div class="el-upload__text">
            拖拽文件到此处或<em>点击上传</em>
          </div>
        </el-upload>

        <!-- 上传进度显示 -->
        <div v-if="uploadLoading" class="upload-progress">
          <el-progress 
            :percentage="uploadProgress" 
            :status="uploadProgress === 100 ? 'success' : ''"
          />
          <div class="upload-status">
            <p>{{ uploadStatus }}</p>
            <p v-if="currentUploadingFile" class="current-file">
              当前文件: {{ currentUploadingFile }}
            </p>
          </div>
        </div>

        <template #footer>
          <el-button @click="uploadDialogVisible = false">
            取消
          </el-button>
          <el-button
            type="primary"
            :loading="uploadLoading"
            @click="submitUpload"
          >
            确认上传
          </el-button>
        </template>
      </el-dialog>

      <div class="table-wrapper">
        <el-table :data="tableData" @selection-change="handleSelectionChange" @sort-change="handleSortChange">
          <el-table-column type="selection" width="50" align="center" />
          <el-table-column label="序号" align="center" width="80">
            <template #default="scope">
              {{ (paginationData.currentPage - 1) * paginationData.pageSize + scope.$index + 1 }}
            </template>
          </el-table-column>
          <el-table-column prop="name" label="文档名" align="center" sortable="custom">
            <template #default="scope">
              <div class="file-name-cell" @dblclick="scope.row.type === 'folder' ? enterFolder(scope.row) : null">
                <el-icon class="file-icon" :class="{ 'folder-icon': scope.row.type === 'folder' }">
                  <component :is="getFileIcon(scope.row)" />
                </el-icon>
                <span 
                  :class="{ 'folder-name': scope.row.type === 'folder', 'file-name': scope.row.type !== 'folder' }"
                  :title="scope.row.type === 'folder' ? '双击进入文件夹' : scope.row.name"
                >
                  {{ scope.row.name }}
                </span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="大小" align="center" width="120" sortable="custom">
            <template #default="scope">
              <span v-if="scope.row.type === 'folder'">-</span>
              <span v-else>{{ formatFileSize(scope.row.size) }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="type" label="类型" align="center" width="120" sortable="custom">
            <template #default="scope">
              <el-tag v-if="scope.row.type === 'folder'" type="warning">文件夹</el-tag>
              <el-tag v-else type="info">{{ scope.row.type }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="create_date" label="创建时间" align="center" width="180" sortable="custom" />
          <el-table-column fixed="right" label="操作" width="180" align="center">
            <template #default="scope">
              <el-button 
                v-if="scope.row.type === 'folder'" 
                type="primary" 
                text 
                bg 
                size="small" 
                :icon="Folder" 
                @click="enterFolder(scope.row)"
              >
                进入
              </el-button>
              <template v-else>
                <el-button type="primary" text bg size="small" :icon="Download" @click="handleDownload(scope.row)">
                  下载
                </el-button>
              </template>
              <el-button type="danger" text bg size="small" :icon="Delete" @click="handleDelete(scope.row)">
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
      <div class="pager-wrapper">
        <el-pagination
          background
          :layout="paginationData.layout"
          :page-sizes="paginationData.pageSizes"
          :total="paginationData.total"
          :page-size="paginationData.pageSize"
          :current-page="paginationData.currentPage"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>
  </div>
</template>

<style lang="scss" scoped>
.el-alert {
  margin-bottom: 20px;
}

.search-wrapper {
  margin-bottom: 20px;
  :deep(.el-card__body) {
    padding-bottom: 2px;
  }
}

.toolbar-wrapper {
  display: flex;
  justify-content: space-between;
  margin-bottom: 20px;
}

.table-wrapper {
  margin-bottom: 20px;
}

.pager-wrapper {
  display: flex;
  justify-content: flex-end;
}

.folder-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.folder-label {
  font-weight: 600;
}

.upload-info {
  margin-bottom: 20px;
  text-align: center;
}

.folder-tree-container {
  height: 300px;
  overflow-y: auto;
}

.root-folder {
  margin-bottom: 10px;
}

.tree-node {
  display: flex;
  align-items: center;
  gap: 10px;
}

.node-label {
  flex-grow: 1;
}

.empty-tree {
  text-align: center;
  padding: 20px;
}

.breadcrumb-wrapper {
  margin-bottom: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.current-folder {
  font-weight: bold;
  color: #409eff !important;
}

.file-name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.file-icon {
  font-size: 18px;
}

.folder-icon {
  color: #f39c12;
}

.folder-name {
  color: #409eff;
  font-weight: 600;
  cursor: pointer;
}

.folder-name:hover {
  text-decoration: underline;
}

.file-name {
  color: #606266;
}

.folder-info {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.folder-label {
  font-weight: 600;
  white-space: nowrap;
}

.upload-progress {
  margin-top: 20px;
  padding: 15px;
  background-color: #f8f9fa;
  border-radius: 4px;
}

.upload-status {
  margin-top: 10px;
  text-align: center;
  color: #606266;
  font-size: 14px;
}

.current-file {
  margin-top: 5px;
  color: #409eff;
  font-weight: 500;
}
</style>

<style>
/* 全局样式 - 确保弹窗样式正确 */
.el-message-box {
  max-width: 500px !important;
  width: auto !important;
  min-width: 420px;
  border-radius: 8px;
  overflow: visible;
}
.delete-confirm-dialog {
  max-width: 500px !important;
  width: auto !important;
  min-width: 420px;
  border-radius: 8px;
  overflow: visible;
}

.delete-confirm-dialog .el-message-box__header {
  padding: 15px 20px;
  background-color: #f8f9fa;
  border-bottom: 1px solid #ebeef5;
  border-radius: 8px 8px 0 0;
}

.delete-confirm-dialog .el-message-box__title {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.delete-confirm-dialog .el-message-box__content {
  padding: 20px;
  max-height: 300px;
  overflow-y: auto;
  word-break: break-word;
}

.delete-confirm-dialog .el-message-box__message {
  font-size: 16px;
  line-height: 1.6;
  color: #606266;
  padding: 0;
  margin: 0;
  word-wrap: break-word;
}

.delete-confirm-dialog .el-message-box__message p {
  margin: 0;
  padding: 0;
}

.delete-confirm-dialog .el-message-box__btns {
  padding: 12px 20px;
  border-top: 1px solid #ebeef5;
  border-radius: 0 0 8px 8px;
  background-color: #f8f9fa;
}

.delete-confirm-dialog .el-button {
  padding: 9px 20px;
  font-size: 14px;
  border-radius: 4px;
  transition: all 0.3s;
}

.delete-confirm-dialog .el-button--primary {
  background-color: #f56c6c;
  border-color: #f56c6c;
}

.delete-confirm-dialog .el-button--primary:hover,
.delete-confirm-dialog .el-button--primary:focus {
  background-color: #f78989;
  border-color: #f78989;
}

.delete-confirm-dialog .el-message-box__status {
  display: none !important;
}

.toolbar-wrapper {
  display: flex;
  justify-content: space-between;
  margin-bottom: 20px;

  .el-button {
    margin-right: 10px;
  }
}

.upload-dialog {
  .el-upload-dragger {
    width: 100%;
    padding: 20px;
  }
}
</style>
