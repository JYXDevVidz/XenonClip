// src/static/js/app.js
class XenonClipApp {
    constructor() {
        this.items = [];
        this.categories = [];
        this.currentCategory = '';
        this.searchText = '';
        
        this.init();
    }
    
    async init() {
        this.bindEvents();
        await this.loadCategories();
        await this.loadItems();
        this.updateStatus('就绪');
    }
    
    bindEvents() {
        // 搜索框事件
        document.getElementById('searchInput').addEventListener('input', (e) => {
            this.searchText = e.target.value;
            this.filterAndDisplayItems();
        });
        
        // 分类过滤事件
        document.getElementById('categoryFilter').addEventListener('change', (e) => {
            this.currentCategory = e.target.value;
            this.filterAndDisplayItems();
        });
        
        // 设置按钮事件
        document.getElementById('settingsBtn').addEventListener('click', () => {
            this.showSettings();
        });
        
        // 手动分类按钮事件
        document.getElementById('manualClassifyBtn').addEventListener('click', () => {
            this.showManualClassifyModal();
        });
        
        // 设置对话框事件
        document.getElementById('closeSettingsBtn').addEventListener('click', () => {
            this.hideSettings();
        });
        
        document.getElementById('cancelSettingsBtn').addEventListener('click', () => {
            this.hideSettings();
        });
        
        document.getElementById('settingsForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.saveSettings();
        });
        
        // 分类调度变化事件
        document.getElementById('classifySchedule').addEventListener('change', (e) => {
            const timePickerDiv = document.getElementById('timePickerDiv');
            if (e.target.value === 'daily') {
                timePickerDiv.classList.remove('hidden');
            } else {
                timePickerDiv.classList.add('hidden');
            }
        });
        
        // 定期刷新数据
        setInterval(() => {
            this.loadItems();
        }, 5000);
        
        // 点击外部关闭下拉菜单
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.category-dropdown-container')) {
                document.querySelectorAll('.category-dropdown').forEach(dropdown => {
                    dropdown.style.display = 'none';
                });
            }
        });
    }
    
    async loadCategories() {
        try {
            const response = await fetch('/api/categories');
            const result = await response.json();
            
            if (result.success) {
                this.categories = result.data;
                this.updateCategoryFilter();
                this.updateCategoryList();
            }
        } catch (error) {
            console.error('加载分类失败:', error);
        }
    }
    
    async loadItems() {
        try {
            const params = new URLSearchParams();
            if (this.currentCategory) {
                params.append('category', this.currentCategory);
            }
            if (this.searchText) {
                params.append('search', this.searchText);
            }
            
            const response = await fetch(`/api/items?${params}`);
            const result = await response.json();
            
            if (result.success) {
                this.items = result.data;
                this.displayItems(this.items);
                this.updateItemCount(this.items.length);
            }
        } catch (error) {
            console.error('加载条目失败:', error);
        }
    }
    
    filterAndDisplayItems() {
        let filtered = this.items;
        
        if (this.currentCategory) {
            filtered = filtered.filter(item => item.category === this.currentCategory);
        }
        
        if (this.searchText) {
            const searchLower = this.searchText.toLowerCase();
            filtered = filtered.filter(item => 
                item.content.toLowerCase().includes(searchLower) ||
                item.category.toLowerCase().includes(searchLower)
            );
        }
        
        this.displayItems(filtered);
        this.updateItemCount(filtered.length);
    }
    
    displayItems(items) {
        const container = document.getElementById('clipboardList');
        
        if (items.length === 0) {
            container.innerHTML = `
                <div class="text-center py-8 text-gray-500">
                    <i class="fas fa-clipboard text-4xl mb-4"></i>
                    <p>暂无剪贴板记录</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = items.map(item => this.renderItem(item)).join('');
        
        // 绑定点击事件
        items.forEach(item => {
            const element = document.getElementById(`item-${item.id}`);
            if (element) {
                element.addEventListener('click', () => this.copyItem(item.id));
            }
            
            // 收藏按钮事件
            const favoriteBtn = document.getElementById(`favorite-${item.id}`);
            if (favoriteBtn) {
                favoriteBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.toggleFavorite(item.id);
                });
            }
            
            // 删除按钮事件
            const deleteBtn = document.getElementById(`delete-${item.id}`);
            if (deleteBtn) {
                deleteBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.deleteItem(item.id);
                });
            }
            
            // 分类标签点击事件
            const categoryTag = document.getElementById(`category-${item.id}`);
            if (categoryTag) {
                categoryTag.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.toggleCategoryDropdown(item.id);
                });
            }
        });
        
        // 绑定分类下拉菜单事件
        document.querySelectorAll('.category-option').forEach(option => {
            option.addEventListener('click', (e) => {
                e.stopPropagation();
                const itemId = parseInt(option.dataset.id);
                const category = option.dataset.category;
                this.updateItemCategory(itemId, category);
            });
        });
    }
    
    renderItem(item) {
        const truncatedContent = item.content.length > 100 
            ? item.content.substring(0, 100) + '...'
            : item.content;
        
        const createdAt = new Date(item.created_at).toLocaleString();
        const favoriteClass = item.is_favorite ? 'text-yellow-500' : 'text-gray-400';
        const sensitiveIcon = item.is_sensitive ? '<i class="fas fa-shield-alt text-red-500 mr-2"></i>' : '';
        
        return `
            <div id="item-${item.id}" class="bg-white rounded-lg p-4 shadow-sm hover:shadow-md transition-shadow cursor-pointer border">
                <div class="flex justify-between items-start mb-3">
                    <div class="flex-1">
                        <div class="text-sm font-medium text-gray-900 mb-1">
                            ${sensitiveIcon}${this.escapeHtml(truncatedContent)}
                        </div>
                        <div class="flex items-center space-x-2 text-xs text-gray-500">
                            <div class="relative category-dropdown-container">
                                <span id="category-${item.id}" class="bg-blue-100 text-blue-800 px-2 py-1 rounded cursor-pointer hover:bg-blue-200 transition-colors">${item.category}</span>
                                <div id="dropdown-${item.id}" class="category-dropdown absolute left-0 mt-1 bg-white shadow-lg rounded-lg border z-10 w-48" style="display: none;">
                                    <div class="p-2">
                                        <div class="text-xs font-medium text-gray-700 mb-2">选择分类:</div>
                                        ${this.renderCategoryOptions(item.id)}
                                        <div class="border-t pt-2 mt-2">
                                            <input type="text" id="newCategory-${item.id}" placeholder="新分类名称" class="w-full px-2 py-1 text-xs border rounded">
                                            <button onclick="app.createAndApplyCategory(${item.id})" class="w-full mt-1 px-2 py-1 text-xs bg-green-500 text-white rounded hover:bg-green-600">创建并应用</button>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <span>${createdAt}</span>
                            <span>使用 ${item.access_count} 次</span>
                        </div>
                    </div>
                    <div class="flex items-center space-x-2 ml-4">
                        <button id="favorite-${item.id}" class="p-1 hover:bg-gray-100 rounded transition-colors">
                            <i class="fas fa-star ${favoriteClass}"></i>
                        </button>
                        <button id="delete-${item.id}" class="p-1 hover:bg-gray-100 rounded text-red-500 hover:text-red-700 transition-colors">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;
    }
    
    renderCategoryOptions(itemId) {
        return this.categories.map(cat => 
            `<div class="py-1 px-2 hover:bg-gray-100 text-sm cursor-pointer category-option rounded" 
                  data-id="${itemId}" data-category="${cat.name}">${cat.name}</div>`
        ).join('');
    }
    
    toggleCategoryDropdown(itemId) {
        const dropdown = document.getElementById(`dropdown-${itemId}`);
        const isVisible = dropdown.style.display !== 'none';
        
        // 隐藏所有下拉菜单
        document.querySelectorAll('.category-dropdown').forEach(d => {
            d.style.display = 'none';
        });
        
        // 切换当前下拉菜单
        if (!isVisible) {
            dropdown.style.display = 'block';
        }
    }
    
    async updateItemCategory(itemId, category) {
        try {
            const response = await fetch(`/api/items/${itemId}/category`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ category })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.updateStatus(`已将项目分类为 ${category}`);
                await this.loadItems();
                await this.loadCategories();
                
                // 隐藏下拉菜单
                document.querySelectorAll('.category-dropdown').forEach(d => {
                    d.style.display = 'none';
                });
                
                setTimeout(() => this.updateStatus('就绪'), 2000);
            }
        } catch (error) {
            console.error('更新分类失败:', error);
            this.updateStatus('更新分类失败');
        }
    }
    
    async createAndApplyCategory(itemId) {
        const input = document.getElementById(`newCategory-${itemId}`);
        const categoryName = input.value.trim();
        
        if (!categoryName) {
            alert('请输入分类名称');
            return;
        }
        
        try {
            // 创建新分类
            const createResponse = await fetch('/api/categories', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ name: categoryName })
            });
            
            if (createResponse.ok) {
                await this.loadCategories();
                await this.updateItemCategory(itemId, categoryName);
                input.value = '';
            }
        } catch (error) {
            console.error('创建分类失败:', error);
            this.updateStatus('创建分类失败');
        }
    }
    
    updateCategoryFilter() {
        const select = document.getElementById('categoryFilter');
        select.innerHTML = '<option value="">所有分类</option>' +
            this.categories.map(cat => 
                `<option value="${cat.name}">${cat.name} (${cat.item_count})</option>`
            ).join('');
    }
    
    updateCategoryList() {
        const container = document.getElementById('categoryList');
        container.innerHTML = this.categories.map(cat => `
            <div class="flex items-center justify-between p-2 rounded hover:bg-gray-50 cursor-pointer category-item transition-colors" data-category="${cat.name}">
                <span class="text-sm font-medium">${cat.name}</span>
                <span class="text-xs text-gray-500 bg-gray-200 px-2 py-1 rounded">${cat.item_count}</span>
            </div>
        `).join('');
        
        // 绑定分类点击事件
        container.querySelectorAll('.category-item').forEach(item => {
            item.addEventListener('click', () => {
                const category = item.dataset.category;
                this.currentCategory = this.currentCategory === category ? '' : category;
                document.getElementById('categoryFilter').value = this.currentCategory;
                this.filterAndDisplayItems();
                
                // 更新选中状态
                container.querySelectorAll('.category-item').forEach(ci => {
                    ci.classList.remove('bg-blue-50', 'border-blue-200');
                });
                if (this.currentCategory === category) {
                    item.classList.add('bg-blue-50', 'border-blue-200');
                }
            });
        });
    }
    
    async copyItem(itemId) {
        try {
            const response = await fetch(`/api/items/${itemId}/copy`, {
                method: 'POST'
            });
            const result = await response.json();
            
            if (result.success) {
                this.updateStatus('已复制到剪贴板');
                setTimeout(() => this.updateStatus('就绪'), 2000);
                await this.loadItems(); // 刷新访问次数
            }
        } catch (error) {
            console.error('复制失败:', error);
            this.updateStatus('复制失败');
        }
    }
    
    async toggleFavorite(itemId) {
        try {
            const response = await fetch(`/api/items/${itemId}/favorite`, {
                method: 'POST'
            });
            const result = await response.json();
            
            if (result.success) {
                await this.loadItems();
            }
        } catch (error) {
            console.error('切换收藏失败:', error);
        }
    }
    
    async deleteItem(itemId) {
        if (!confirm('确认删除此条目？')) {
            return;
        }
        
        try {
            const response = await fetch(`/api/items/${itemId}`, {
                method: 'DELETE'
            });
            const result = await response.json();
            
            if (result.success) {
                await this.loadItems();
                await this.loadCategories();
                this.updateStatus('条目已删除');
                setTimeout(() => this.updateStatus('就绪'), 2000);
            }
        } catch (error) {
            console.error('删除失败:', error);
        }
    }
    
    showManualClassifyModal() {
        // 移除已存在的模态框
        const existingModal = document.getElementById('manualClassifyModal');
        if (existingModal) {
            document.body.removeChild(existingModal);
        }
        
        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center';
        modal.id = 'manualClassifyModal';
        
        const unclassifiedCount = this.items.filter(item => item.category === '未分类').length;
        
        const content = `
            <div class="bg-white rounded-lg p-6 w-96">
                <div class="flex justify-between items-center mb-4">
                    <h3 class="text-lg font-semibold">批量手动分类</h3>
                    <button id="closeManualClassifyBtn" class="text-gray-400 hover:text-gray-600">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                
                <p class="text-sm text-gray-600 mb-4">
                    发现 <strong>${unclassifiedCount}</strong> 个未分类项目。选择一个分类将它们批量设置：
                </p>
                
                <select id="batchCategorySelect" class="w-full px-3 py-2 border border-gray-300 rounded-md mb-4">
                    <option value="">选择分类...</option>
                    ${this.categories.map(cat => `<option value="${cat.name}">${cat.name}</option>`).join('')}
                </select>
                
                <div class="mb-4">
                    <input type="text" id="newBatchCategory" placeholder="或创建新分类..." class="w-full px-3 py-2 border border-gray-300 rounded-md">
                </div>
                
                <div class="flex justify-end space-x-3">
                    <button id="cancelManualClassifyBtn" class="px-4 py-2 text-gray-600 border border-gray-300 rounded-md hover:bg-gray-50">
                        取消
                    </button>
                    <button id="confirmManualClassifyBtn" class="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600">
                        应用分类
                    </button>
                </div>
            </div>
        `;
        
        modal.innerHTML = content;
        document.body.appendChild(modal);
        
        // 绑定事件
        document.getElementById('closeManualClassifyBtn').addEventListener('click', () => {
            document.body.removeChild(modal);
        });
        
        document.getElementById('cancelManualClassifyBtn').addEventListener('click', () => {
            document.body.removeChild(modal);
        });
        
        document.getElementById('confirmManualClassifyBtn').addEventListener('click', async () => {
            const selectedCategory = document.getElementById('batchCategorySelect').value;
            const newCategory = document.getElementById('newBatchCategory').value.trim();
            
            let categoryToApply = selectedCategory || newCategory;
            
            if (!categoryToApply) {
                alert('请选择或创建一个分类');
                return;
            }
            
            // 如果是新分类，先创建
            if (newCategory && !selectedCategory) {
                try {
                    await fetch('/api/categories', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ name: newCategory })
                    });
                    await this.loadCategories();
                } catch (error) {
                    console.error('创建分类失败:', error);
                    alert('创建分类失败');
                    return;
                }
            }
            
            await this.batchUpdateCategory(categoryToApply);
            document.body.removeChild(modal);
        });
    }
    
    async batchUpdateCategory(category) {
        try {
            this.updateStatus('正在批量更新分类...');
            
            // 获取未分类的项目
            const unclassifiedItems = this.items.filter(item => item.category === '未分类');
            
            let successCount = 0;
            
            // 逐个更新
            for (const item of unclassifiedItems) {
                try {
                    const response = await fetch(`/api/items/${item.id}/category`, {
                        method: 'PUT',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ category })
                    });
                    
                    if (response.ok) {
                        successCount++;
                    }
                } catch (error) {
                    console.error(`更新项目 ${item.id} 失败:`, error);
                }
            }
            
            await this.loadItems();
            await this.loadCategories();
            
            this.updateStatus(`已将 ${successCount} 个项目分类为 ${category}`);
            setTimeout(() => this.updateStatus('就绪'), 3000);
            
        } catch (error) {
            console.error('批量更新分类失败:', error);
            this.updateStatus('批量更新分类失败');
        }
    }
    
    async showSettings() {
        try {
            const response = await fetch('/api/settings');
            const result = await response.json();
            
            if (result.success) {
                const settings = result.data;
                document.getElementById('autoClassify').checked = settings.auto_classify;
                document.getElementById('classifySchedule').value = settings.classify_schedule;
                document.getElementById('classifyTime').value = settings.classify_time;
                document.getElementById('retentionDays').value = settings.retention_days;
                document.getElementById('enableSensitiveDetection').checked = settings.enable_sensitive_detection;
                
                // 显示/隐藏时间选择器
                const timePickerDiv = document.getElementById('timePickerDiv');
                if (settings.classify_schedule === 'daily') {
                    timePickerDiv.classList.remove('hidden');
                } else {
                    timePickerDiv.classList.add('hidden');
                }
            }
            
            document.getElementById('settingsModal').classList.remove('hidden');
        } catch (error) {
            console.error('加载设置失败:', error);
        }
    }
    
    hideSettings() {
        document.getElementById('settingsModal').classList.add('hidden');
    }
    
    async saveSettings() {
        try {
            const settings = {
                auto_classify: document.getElementById('autoClassify').checked,
                classify_schedule: document.getElementById('classifySchedule').value,
                classify_time: document.getElementById('classifyTime').value,
                retention_days: parseInt(document.getElementById('retentionDays').value),
                enable_sensitive_detection: document.getElementById('enableSensitiveDetection').checked
            };
            
            const response = await fetch('/api/settings', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(settings)
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.hideSettings();
                this.updateStatus('设置已保存');
                setTimeout(() => this.updateStatus('就绪'), 2000);
            }
        } catch (error) {
            console.error('保存设置失败:', error);
            this.updateStatus('保存设置失败');
        }
    }
    
    updateStatus(text) {
        document.getElementById('statusText').textContent = text;
    }
    
    updateItemCount(count) {
        document.getElementById('itemCount').textContent = `共 ${count} 条记录`;
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// 全局变量，方便在HTML中调用
let app;

// 启动应用
document.addEventListener('DOMContentLoaded', () => {
    app = new XenonClipApp();
});