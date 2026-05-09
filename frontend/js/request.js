// ==================== 请求封装模块 ====================
// 文件: api.js 或直接嵌入在 <script> 标签中

const ApiClient = (function() {
    // ========== 配置项（根据您的后端地址修改） ==========
    const CONFIG = {
        BASE_URL: 'http://localhost:8088',           // 后端基础地址
        TIMEOUT: 15000,                               // 请求超时时间(ms)
        RETRY_COUNT: 2,                               // 失败重试次数
        RETRY_DELAY: 1000,                            // 重试间隔(ms)
    };

    // 存储ADB设备信息
    let currentDevice = {
        serial: null,                                 // 设备序列号
        status: 'disconnected',                       // connected | disconnected | unauthorized
        model: '',
        androidVersion: '',
        resolution: '',
    };

    // ========== 核心请求方法 ==========
    /**
     * 基础请求封装
     * @param {string} endpoint - API路径，如 '/api/screenshot'
     * @param {object} options - fetch选项
     * @returns {Promise<any>}
     */
    async function request(endpoint, options = {}) {
        const url = `${CONFIG.BASE_URL}${endpoint}`;
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
            },
            signal: AbortSignal.timeout(CONFIG.TIMEOUT),
        };

        const mergedOptions = { ...defaultOptions, ...options };
        // 合并headers
        if (options.headers) {
            mergedOptions.headers = { ...defaultOptions.headers, ...options.headers };
        }

        let lastError = null;
        for (let attempt = 0; attempt <= CONFIG.RETRY_COUNT; attempt++) {
            try {
                if (attempt > 0) {
                    addLog(`请求重试 (${attempt}/${CONFIG.RETRY_COUNT}): ${endpoint}`, 'warn');
                    await sleep(CONFIG.RETRY_DELAY * attempt);
                }
                const response = await fetch(url, mergedOptions);
                if (!response.ok) {
                    const errorBody = await response.text().catch(() => '');
                    throw new Error(`HTTP ${response.status}: ${errorBody || response.statusText}`);
                }
                const contentType = response.headers.get('content-type') || '';
                if (contentType.includes('application/json')) {
                    return await response.json();
                }
                return await response.text();
            } catch (error) {
                lastError = error;
                if (error.name === 'TimeoutError' || error.name === 'AbortError') {
                    lastError = new Error(`请求超时: ${endpoint}`);
                }
                // 非网络错误不重试
                if (error.message.includes('HTTP 4')) {
                    throw error;
                }
            }
        }
        throw lastError || new Error(`请求失败: ${endpoint}`);
    }

    /**
     * GET请求
     */
    async function get(endpoint, params = {}) {
        const queryString = Object.entries(params)
            .filter(([_, v]) => v !== undefined && v !== null)
            .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
            .join('&');
        const fullEndpoint = queryString ? `${endpoint}?${queryString}` : endpoint;
        return request(fullEndpoint, { method: 'GET' });
    }

    /**
     * POST请求
     */
    async function post(endpoint, data = {}) {
        return request(endpoint, {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    /**
     * POST上传文件/表单数据
     */
    async function upload(endpoint, formData) {
        return request(endpoint, {
            method: 'POST',
            headers: {},  // 让浏览器自动设置multipart边界
            body: formData,
        });
    }

    /**
     * DELETE请求
     */
    async function del(endpoint) {
        return request(endpoint, { method: 'DELETE' });
    }

    function sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    // ========== ADB相关API ==========
    const ADB_API = {
        /**
         * 获取ADB连接状态
         * @returns {Promise<{connected: boolean, devices: Array}>}
         */
        async getStatus() {
            try {
                const result = await get('/api/adb/status');
                if (result.devices && result.devices.length > 0) {
                    currentDevice = {
                        serial: result.devices[0].serial,
                        status: result.devices[0].status || 'connected',
                        model: result.devices[0].model || '',
                        androidVersion: result.devices[0].androidVersion || '',
                        resolution: result.devices[0].resolution || '',
                    };
                } else {
                    currentDevice.status = 'disconnected';
                }
                return result;
            } catch (error) {
                currentDevice.status = 'disconnected';
                throw error;
            }
        },

        /**
         * 刷新ADB连接
         */
        async refresh() {
            return post('/api/adb/refresh');
        },

        /**
         * 连接指定设备
         * @param {string} serial - 设备序列号
         */
        async connect(serial) {
            return post('/api/adb/connect', { serial });
        },

        /**
         * 断开设备
         */
        async disconnect() {
            return post('/api/adb/disconnect');
        },

        /**
         * 获取当前设备信息
         */
        getCurrentDevice() {
            return { ...currentDevice };
        },
    };

    // ========== 截图相关API ==========
    const SCREENSHOT_API = {
        /**
         * 执行一次截图（通过ADB）
         * @param {object} options - 截图选项
         * @param {string} options.savePath - 保存路径（可选）
         * @param {boolean} options.returnBase64 - 是否返回base64（默认true）
         * @returns {Promise<{id: string, base64?: string, path?: string, width: number, height: number}>}
         */
        async capture(options = {}) {
            const defaultOpts = { returnBase64: true };
            return post('/api/screenshot/capture', { ...defaultOpts, ...options });
        },

        /**
         * 获取截图列表
         * @param {number} limit - 获取最近N张
         */
        async getList(limit = 20) {
            return get('/api/screenshot/list', { limit });
        },

        /**
         * 获取指定截图文件
         * @param {string} screenshotId - 截图ID
         * @returns {Promise<{base64: string, width: number, height: number}>}
         */
        async getById(screenshotId) {
            return get(`/api/screenshot/${screenshotId}`);
        },

        /**
         * 删除截图
         * @param {string} screenshotId - 截图ID
         */
        async delete(screenshotId) {
            return del(`/api/screenshot/${screenshotId}`);
        },

        /**
         * 开始实时截图流（轮询模式）
         * @param {number} interval - 间隔(ms)，默认2000
         * @returns {Promise<{streamId: string}>}
         */
        async startStream(interval = 2000) {
            return post('/api/screenshot/stream/start', { interval });
        },

        /**
         * 停止实时截图流
         */
        async stopStream() {
            return post('/api/screenshot/stream/stop');
        },

        /**
         * 获取最新一帧截图
         * @returns {Promise<{base64: string, timestamp: number}>}
         */
        async getLatestFrame() {
            return get('/api/screenshot/stream/latest');
        },
    };

    // ========== ROI坐标相关API ==========
    const ROI_API = {
        /**
         * 保存ROI坐标到指定截图
         * @param {string} screenshotId - 截图ID
         * @param {Array} rectangles - 矩形框数组 [{name, x, y, width, height}]
         */
        async save(screenshotId, rectangles) {
            return post(`/api/roi/${screenshotId}`, { rectangles });
        },

        /**
         * 获取指定截图的ROI坐标
         * @param {string} screenshotId - 截图ID
         * @returns {Promise<{rectangles: Array}>}
         */
        async getByShotId(screenshotId) {
            return get(`/api/roi/${screenshotId}`);
        },

        /**
         * 导出ROI模板（批量）
         * @param {Array<string>} screenshotIds - 截图ID列表（空则导出全部）
         * @returns {Promise<Blob>} - 直接触发下载
         */
        async exportAll(screenshotIds = []) {
            const queryParams = screenshotIds.length > 0 ?
                `?ids=${screenshotIds.join(',')}` : '';
            const url = `${CONFIG.BASE_URL}/api/roi/export${queryParams}`;
            const response = await fetch(url);
            if (!response.ok) throw new Error('导出失败');
            const blob = await response.blob();
            const downloadUrl = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = downloadUrl;
            a.download = `roi_templates_${Date.now()}.json`;
            a.click();
            URL.revokeObjectURL(downloadUrl);
            return { success: true };
        },

        /**
         * 导入ROI模板
         * @param {File} jsonFile - JSON文件
         */
        async importFile(jsonFile) {
            const formData = new FormData();
            formData.append('file', jsonFile);
            return upload('/api/roi/import', formData);
        },
    };

    // ========== 自动化任务相关API ==========
    const TASK_API = {
        /**
         * 获取所有任务配置
         */
        async getList() {
            return get('/api/tasks');
        },

        /**
         * 保存任务配置
         * @param {object} task - 任务对象
         */
        async save(task) {
            return post('/api/tasks', task);
        },

        /**
         * 启动任务
         * @param {string} taskId - 任务ID
         */
        async start(taskId) {
            return post(`/api/tasks/${taskId}/start`);
        },

        /**
         * 停止任务
         * @param {string} taskId - 任务ID
         */
        async stop(taskId) {
            return post(`/api/tasks/${taskId}/stop`);
        },

        /**
         * 删除任务
         * @param {string} taskId - 任务ID
         */
        async delete(taskId) {
            return del(`/api/tasks/${taskId}`);
        },

        /**
         * 获取任务运行状态
         * @param {string} taskId - 任务ID
         */
        async getStatus(taskId) {
            return get(`/api/tasks/${taskId}/status`);
        },
    };

    // ========== 设置相关API ==========
    const SETTINGS_API = {
        /**
         * 获取所有设置
         */
        async get() {
            return get('/api/settings');
        },

        /**
         * 保存设置
         * @param {object} settings - 设置键值对
         */
        async save(settings) {
            return post('/api/settings', settings);
        },

        /**
         * 测试ADB连接
         */
        async testConnection() {
            return post('/api/settings/test-adb');
        },
    };

    // ========== 日志相关API ==========
    const LOG_API = {
        /**
         * 获取服务端日志
         * @param {number} limit - 获取条数
         */
        async get(limit = 200) {
            return get('/api/logs', { limit });
        },

        /**
         * 清空服务端日志
         */
        async clear() {
            return del('/api/logs');
        },
    };

    // ========== 健康检查 ==========
    async function healthCheck() {
        try {
            const result = await get('/api/health');
            return { online: true, ...result };
        } catch {
            return { online: false };
        }
    }

    // ========== 公开API ==========
    return {
        // 配置
        CONFIG,
        updateBaseUrl(url) {
            CONFIG.BASE_URL = url;
            addLog(`API地址已更新: ${url}`, 'info');
        },

        // 健康检查
        healthCheck,

        // 各模块API
        adb: ADB_API,
        screenshot: SCREENSHOT_API,
        roi: ROI_API,
        task: TASK_API,
        settings: SETTINGS_API,
        log: LOG_API,

        // 原始request方法（供自定义请求）
        request,
        get,
        post,
        upload,
        del,
    };
})();


// ==================== 使用示例 ====================
// 以下代码展示如何在现有页面中使用封装好的ApiClient

// 示例1: 替换截图按钮功能
async function captureScreenshotWithAPI() {
    try {
        addLog('正在通过API获取截图...', 'info');
        const result = await ApiClient.screenshot.capture({ returnBase64: true });

        // 将base64显示到实时截图区域
        const area = document.getElementById('liveScreenshotArea');
        if (area && result.base64) {
            area.innerHTML = `<img src="${result.base64}" alt="截图">`;
        }

        // 同时加载到ROI编辑器
        if (result.base64) {
            const img = new Image();
            img.onload = () => {
                roiImage = img;
                roiRectangles = [];  // 新截图清除旧ROI
                selectedRoiId = null;
                updateRoiDisplay();
                renderRoiList();
                addLog(`截图已就绪: ${result.id}`, 'info');
                showToast('截图成功，可在ROI编辑器标记区域');

                // 尝试加载该截图的已有ROI模板
                loadROIForScreenshot(result.id);
            };
            img.src = result.base64;
        }

        addLog(`截图成功: ${result.id}`, 'info');
        return result;
    } catch (error) {
        addLog(`截图失败: ${error.message}`, 'error');
        showToast('截图失败，请检查ADB连接');
        throw error;
    }
}

// 示例2: 加载截图对应的ROI模板
async function loadROIForScreenshot(screenshotId) {
    try {
        const data = await ApiClient.roi.getByShotId(screenshotId);
        if (data.rectangles && data.rectangles.length > 0) {
            roiRectangles = data.rectangles.map(r => ({
                id: r.id || roiGenId(),
                name: r.name || 'ROI',
                x: r.x,
                y: r.y,
                width: r.width,
                height: r.height,
            }));
            renderRoiCanvas();
            renderRoiList();
            addLog(`已加载${roiRectangles.length}个ROI模板`, 'info');
        }
    } catch (error) {
        // 该截图可能没有ROI模板，正常情况
        console.log('未找到已有ROI模板');
    }
}

// 示例3: 保存ROI到后端
async function saveROIToServer() {
    const screenshotId = 'current_screenshot_id'; // 从当前上下文获取
    try {
        await ApiClient.roi.save(screenshotId, roiRectangles);
        addLog(`ROI已保存到截图: ${screenshotId}`, 'info');
        showToast('ROI坐标已保存');
    } catch (error) {
        addLog(`ROI保存失败: ${error.message}`, 'error');
        showToast('保存失败');
    }
}

// 示例4: 刷新ADB状态
async function refreshAdbStatusWithAPI() {
    try {
        const status = await ApiClient.adb.getStatus();
        const dot = document.getElementById('adbStatusDot');
        const info = document.getElementById('adbDeviceInfo');

        if (dot && info) {
            if (status.connected && status.devices && status.devices.length > 0) {
                const device = status.devices[0];
                dot.className = 'status-dot connected';
                info.textContent = `✅ 设备: ${device.serial} | ${device.model || '未知'} | ${device.resolution || ''}`;
                addLog(`ADB已连接: ${device.serial}`, 'info');
            } else {
                dot.className = 'status-dot disconnected';
                info.textContent = '⚠️ 未检测到设备';
                addLog('ADB未连接', 'warn');
            }
        }
        return status;
    } catch (error) {
        const dot = document.getElementById('adbStatusDot');
        const info = document.getElementById('adbDeviceInfo');
        if (dot && info) {
            dot.className = 'status-dot disconnected';
            info.textContent = `❌ 连接失败: ${error.message}`;
        }
        addLog(`ADB状态获取失败: ${error.message}`, 'error');
    }
}

// 示例5: 启动/停止任务
async function toggleTaskWithAPI(taskId) {
    const statusEl = document.getElementById(`status-${taskId}`);
    if (!statusEl) return;

    const isRunning = statusEl.textContent.includes('运行中');
    try {
        if (isRunning) {
            await ApiClient.task.stop(taskId);
            statusEl.textContent = '已停止';
            statusEl.className = 'card-status stopped';
            addLog(`任务 ${taskId} 已停止`, 'warn');
        } else {
            await ApiClient.task.start(taskId);
            statusEl.textContent = '运行中';
            statusEl.className = 'card-status running';
            addLog(`任务 ${taskId} 已启动`, 'info');
        }
    } catch (error) {
        addLog(`任务操作失败: ${error.message}`, 'error');
        showToast(`操作失败: ${error.message}`);
    }
}

// 示例6: 应用初始化时检查后端是否在线
async function checkBackendHealth() {
    const health = await ApiClient.healthCheck();
    if (health.online) {
        addLog('后端服务已连接', 'info');
        // 进一步初始化：刷新ADB状态、加载任务列表等
        await refreshAdbStatusWithAPI();
    } else {
        addLog('后端服务未启动，部分功能不可用', 'warn');
    }
}


// ==================== 对接现有函数的替换方案 ====================
// 将原有的模拟函数替换为API调用：

// 原 captureScreenshot() → 替换为:
// captureScreenshotWithAPI();

// 原 refreshAdbStatus() → 替换为:
// refreshAdbStatusWithAPI();

// 原 toggleTask(taskId) → 替换为:
// toggleTaskWithAPI(taskId);

// 导出ROI按钮 → 替换为:
// document.getElementById('btnExportRoi')?.addEventListener('click', () => {
//     saveROIToServer();  // 保存到后端
//     // 或调用 ApiClient.roi.exportAll() 下载JSON
// });

// 导出全部按钮 → 替换为:
// document.getElementById('btnExportAll')?.addEventListener('click', () => {
//     ApiClient.roi.exportAll();
// });


// ==================== 修改后端地址 ====================
// 在设置页面或初始化时调用：
// ApiClient.updateBaseUrl('http://192.168.1.100:8088');
