/**
 * 杀手组织老板模拟器 v2 — 前端逻辑
 *
 * 纯按钮操作，无文本输入框。
 * 所有动作通过 POST /api/act 与后端交互。
 */


// 生成/读取唯一会话ID（用于多人隔离）
const SESSION_ID = localStorage.getItem('killer_boss_session') || (function(){
    const id = 's' + Date.now() + '_' + Math.random().toString(36).substr(2, 6);
    localStorage.setItem('killer_boss_session', id);
    return id;
})();

// ============================================================
// 状态
// ============================================================

const API_BASE = window.location.origin;

let STATE = null;
let gameStarted = false;
let loading = false;
let modalState = null;
let currentContractIndex = null;

// ============================================================
// DOM 引用
// ============================================================

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const dom = {
    // Header
    dayBadge: $('#day-badge'),
    orgBadge: $('#org-badge'),
    headerFunds: $('#header-funds'),
    headerRep: $('#header-rep'),
    headerAp: $('#header-ap'),

    // Stats panel
    statFunds: $('#stat-funds'),
    statRep: $('#stat-rep'),
    statRepBar: $('#rep-bar-fill'),
    statApDots: $('#ap-dots'),
    statDay: $('#stat-day'),

    // Narrative
    narrativeContent: $('#narrative-content'),

    // Hitman
    hitmanList: $('#hitman-list'),
    hitmanCount: $('#hitman-count'),

    // Buttons
    btnStart: $('#btn-start'),
    btnContracts: $('#btn-contracts'),
    btnRecruit: $('#btn-recruit'),
    btnDevelop: $('#btn-develop'),
    btnFactions: $('#btn-factions'),
    btnLeaderboard: $('#btn-leaderboard'),
    btnRivals: $('#btn-rivals'),
    btnWeaponShop: $('#btn-weapon-shop'),
    btnTraining: $('#btn-training'),
    btnEndDay: $('#btn-end-day'),
    btnSave: $('#btn-save'),
    btnLoad: $('#btn-load'),
    btnRestart: $('#btn-restart'),
    resetLink: $('#reset-link'),

    // Screens
    startScreen: $('#start-screen'),
    gameUI: $('#game-ui'),

    // Modal
    modalOverlay: $('#modal-overlay'),
    modalHeader: $('#modal-header'),
    modalBody: $('#modal-body'),
    modalClose: $('#modal-close'),

    // Loading
    loadingOverlay: $('#loading-overlay'),
    loadingText: $('#loading-text'),

    // Hitman detail
    hitmanDetail: $('#hitman-detail'),
};

// ============================================================
// API 调用
// ============================================================

const TIMEOUT_MS = 60000;

async function fetchWithTimeout(url, options, timeoutMs) {
    timeoutMs = timeoutMs || TIMEOUT_MS;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
        const resp = await fetch(url, { ...options, signal: controller.signal });
        return resp;
    } finally {
        clearTimeout(timer);
    }
}

async function apiCall(action, params = {}) {
    params = params || {};
    params.session_id = SESSION_ID;
    if (loading) return null;
    setLoading(true);
    try {
        const resp = await fetchWithTimeout(`${API_BASE}/api/act`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action, params }),
        });
        if (!resp.ok) {
            const errText = await resp.text();
            throw new Error(`HTTP ${resp.status}: ${errText}`);
        }
        const data = await resp.json();
        return data;
    } catch (err) {
        console.error('API call failed:', err);
        if (err.name === 'AbortError') {
            appendNarrative('⚠️ 请求超时，请检查网络后重试。', 'system');
        } else {
            appendNarrative(`⚠️ 通讯中断：${err.message}`, 'system');
        }
        return null;
    } finally {
        setLoading(false);
    }
}

async function apiStart() {
    // Pass session_id via query param since apiStart doesn't take params

    if (loading) return null;
    setLoading(true);
    try {
        const resp = await fetchWithTimeout(`${API_BASE}/api/start?session_id=${SESSION_ID}`, { method: 'POST' });
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();
        return data;
    } catch (err) {
        console.error('Start failed:', err);
        if (err.name === 'AbortError') {
            appendNarrative('⚠️ 请求超时，请检查网络后重试。', 'system');
        }
        return null;
    } finally {
        setLoading(false);
    }
}

// ============================================================
// 渲染
// ============================================================

function updateStats(state) {
    STATE = state;

    // Header
    dom.dayBadge.textContent = `第 ${state.day} 天`;
    dom.orgBadge.textContent = `Lv.${state.org_level} ${state.org_level_name}`;
    dom.headerFunds.textContent = formatMoney(state.funds);
    dom.headerRep.textContent = `${state.reputation}/${state.max_reputation}`;
    dom.headerAp.textContent = `${state.ap}/${state.max_ap}`;

    // Stats panel
    dom.statFunds.textContent = formatMoney(state.funds);
    dom.statRep.textContent = `${state.reputation}`;
    dom.statRepBar.style.width = `${(state.reputation / state.max_reputation) * 100}%`;

    // AP dots
    dom.statApDots.innerHTML = '';
    for (let i = 0; i < state.max_ap; i++) {
        const dot = document.createElement('div');
        dot.className = `ap-dot ${i < state.ap ? 'filled' : 'empty'}`;
        dom.statApDots.appendChild(dot);
    }

    // Intel display (in stats panel, add if element exists)
    const intelEl = $('#stat-intel');
    if (intelEl) {
        intelEl.textContent = state.intel || 0;
    }

    dom.statDay.textContent = `第 ${state.day} 天`;

    // Hitmen
    renderHitmen(state.hitmen);

    // Buttons
    updateButtons(state);
}

function renderHitmen(hitmen) {
    dom.hitmanList.innerHTML = '';

    if (!hitmen || hitmen.length === 0) {
        const empty = document.createElement('div');
        empty.className = 'hitman-card empty';
        empty.textContent = '🔫 暂无杀手，去招募吧';
        dom.hitmanList.appendChild(empty);
        dom.hitmanCount.textContent = '0';
        return;
    }

    dom.hitmanCount.textContent = hitmen.length;

    hitmen.forEach((h) => {
        const card = document.createElement('div');
        card.className = 'hitman-card';
        card.dataset.id = h.id;

        const weaponName = h.weapon_id ? STATE.weapons?.find(w => w.id === h.weapon_id)?.name || '' : '';
        const lv = h.lv || 1;
        const exp = h.exp || 0;
        const needExp = lv * 50;

        // Legend title (Lv8 unlock)
        const legend = h.legend_title ? ` [${h.legend_title}]` : '';

        card.innerHTML = `
            <div class="name">
                ${h.name}${legend}
                <span class="spec-badge">${h.specialty}</span>
            </div>
            <div class="details">
                <span>⚔️ Lv.${lv}</span>
                <span>💪 ${h.skill}</span>
                <span>📊 ${Math.round((h.cut||0.2)*100)}%抽</span>
            </div>
            <div class="details" style="font-size:10px;color:#888;">
                ${weaponName ? '🔫 '+weaponName : ''}
                <span>❤️${h.loyalty}</span>
                <span>EXP ${exp}/${needExp}</span>
            </div>
            <span class="status-badge ${h.status}">${statusText(h.status)}</span>
        `;

        card.addEventListener('click', () => showHitmanDetail(h, card));
        dom.hitmanList.appendChild(card);
    });
}

function statusText(status) {
    const map = { idle: '空闲', injured: '受伤', on_mission: '任务中', dead: '死亡' };
    return map[status] || status;
}

function updateButtons(state) {
    const apOk = state.ap > 0;
    const hasHitmen = (state.hitmen || []).length > 0;

    dom.btnRecruit.disabled = !gameStarted || state.game_over || !apOk;
    dom.btnContracts.disabled = !gameStarted || state.game_over;
    dom.btnWeaponShop.disabled = !gameStarted || state.game_over;
    dom.btnLeaderboard.disabled = !gameStarted;
    dom.btnSave.disabled = !gameStarted || state.game_over;
    dom.btnLoad.disabled = !gameStarted || state.game_over;
    dom.btnTraining.disabled = !gameStarted || state.game_over || !apOk || !hasHitmen;
    dom.btnRivals.disabled = !gameStarted || state.game_over;
    dom.btnEndDay.disabled = !gameStarted || state.game_over;
    dom.btnDevelop.disabled = !gameStarted || state.game_over;
    dom.btnFactions.disabled = !gameStarted || state.game_over || state.org_level < 4;
}

function appendNarrative(text, type = 'narrative') {
    const msg = document.createElement('div');
    msg.className = `narrative-msg ${type}`;
    msg.textContent = text;
    dom.narrativeContent.appendChild(msg);
    dom.narrativeContent.scrollTop = dom.narrativeContent.scrollHeight;
}

function clearNarrative() {
    dom.narrativeContent.innerHTML = '';
}

// --- Toast ---
function showToast(msg, durationMs) {
    durationMs = durationMs || 2000;
    let toast = document.getElementById('toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'toast';
        toast.style.cssText = 'position:fixed;bottom:80px;left:50%;transform:translateX(-50%);background:#333;color:#fff;padding:10px 24px;border-radius:8px;font-size:14px;z-index:9999;opacity:0;transition:opacity 0.3s;pointer-events:none;';
        document.body.appendChild(toast);
    }
    toast.textContent = msg;
    toast.style.opacity = '1';
    clearTimeout(toast._timer);
    toast._timer = setTimeout(() => { toast.style.opacity = '0'; }, durationMs);
}

// ============================================================
// Modal 系统
// ============================================================

function showModal(title, contentHtml) {
    dom.modalHeader.innerHTML = `<h2>${title}</h2>`;
    dom.modalBody.innerHTML = contentHtml;
    dom.modalOverlay.classList.remove('hidden');
    dom.modalClose.onclick = closeModal;
    dom.modalOverlay.onclick = (e) => {
        if (e.target === dom.modalOverlay) closeModal();
    };
}

function closeModal() {
    dom.modalOverlay.classList.add('hidden');
    modalState = null;
    setLoading(false);
}

// ============================================================
// 操作处理
// ============================================================

// --- 开始游戏 ---
async function handleStart() {
    const data = await apiStart();
    if (!data) return;

    dom.startScreen.classList.add('hidden');
    dom.gameUI.classList.remove('hidden');

    gameStarted = true;
    updateStats(data.state);
    appendNarrative(data.narrative, 'narrative');
    setLoading(false);

    // 检查主线剧情
    if (data.extra?.main_story) {
        setTimeout(() => showMainStoryModal(data.extra.main_story), 300);
    }
}

// --- 主线剧情 ---
function showMainStoryModal(story) {
    let html = `<div style="margin-bottom:16px;line-height:1.8;">${story.text.replace(/\n/g, '<br>')}</div>`;
    html += '<div style="display:flex;flex-direction:column;gap:8px;">';
    story.choices.forEach((choice, i) => {
        html += `<button class="btn btn-gold" onclick="doResolveStory(${story.level}, ${i})" style="width:100%;">${choice.text}</button>`;
    });
    html += '</div>';
    showModal(`📖 ${story.title}`, html);
}

async function doResolveStory(level, choiceIndex) {
    closeModal();
    const data = await apiCall('resolve_story', { level, choice_index: choiceIndex });
    if (!data) return;
    updateStats(data.state);
    appendNarrative(data.narrative, 'narrative');

    if (data.extra?.ending) {
        appendNarrative(`🎬 结局达成：${data.extra.ending}`, 'game-over');
        disableGameButtons();
    }
    setLoading(false);
}

// --- 契约板 ---
async function handleShowContracts() {
    modalState = 'contracts';
    const data = await apiCall('contracts');
    if (!data) return;

    const contracts = data.extra?.contracts || [];
    if (contracts.length === 0) {
        showModal('📋 契约板', '<p style="color:var(--text-muted)">今天的契约板是空的……</p>');
        return;
    }

    let html = '<p style="margin-bottom:12px;color:var(--text-secondary);">选择要执行的契约：</p>';
    contracts.forEach((c, idx) => {
        const diffClass = { '简单': 'easy', '中等': 'medium', '困难': 'hard', '致命': 'fatal' }[c.difficulty] || 'medium';
        html += `
            <div class="contract-card" data-index="${idx}">
                <div class="contract-title">
                    <span>${c.name}</span>
                    <span class="contract-diff ${diffClass}">${c.difficulty}</span>
                </div>
                <div class="contract-meta">
                    <span>🎯 ${c.required_specialty}</span>
                    <span>⭐ 要求: ${c.reputation_req}</span>
                    <span>💰 ${formatMoney(c.reward)}</span>
                </div>
                <div class="contract-action">
                    <button class="btn btn-gold btn-sm" onclick="handleAssignContract(${idx})">派遣杀手 ➤</button>
                </div>
            </div>
        `;
    });

    showModal('📋 契约板', html);
    setLoading(false);
}

// --- 派遣杀手 + 方案选择 ---
async function handleAssignContract(contractIndex) {
    modalState = 'assign';
    const hitmen = STATE?.hitmen || [];
    const idleHitmen = hitmen.filter(h => h.status === 'idle');

    if (idleHitmen.length === 0) {
        appendNarrative('没有空闲的杀手可以派遣。', 'system');
        closeModal();
        return;
    }

    currentContractIndex = contractIndex;
    const contract = STATE.contracts[contractIndex];
    const orgLevel = STATE.org_level;

    let html = `<p style="margin-bottom:12px;color:var(--text-secondary);">
        契约：<strong>${contract.name}</strong>（${contract.difficulty} · ${contract.required_specialty}）
    </p>
    <p style="margin-bottom:12px;font-size:13px;color:var(--text-muted);">选择派遣的杀手：</p>`;

    const sorted = [...idleHitmen].sort((a, b) => {
        const aMatch = a.specialty === contract.required_specialty ? -1 : 1;
        const bMatch = b.specialty === contract.required_specialty ? -1 : 1;
        return aMatch - bMatch;
    });

    sorted.forEach(h => {
        const isMatch = h.specialty === contract.required_specialty;
        html += `
            <div class="hitman-select-card" onclick="showPlanChoice(${contractIndex}, ${h.id})">
                <div>
                    <span class="sel-name">${h.name}</span>
                    <span class="sel-spec ${isMatch ? 'match' : ''}">
                        ${h.specialty} ${isMatch ? '✓' : ''}
                    </span>
                </div>
                <div style="font-size:12px;color:var(--text-muted);">
                    ⚔️ Lv.${h.skill} · ❤️${h.loyalty}
                </div>
            </div>
        `;
    });

    dom.modalBody.innerHTML = html;
}

async function showPlanChoice(contractIndex, hitmanId) {
    // Lv3以下直接执行
    if (STATE.org_level < 3) {
        await executeAssign(contractIndex, hitmanId, null);
        return;
    }

    // 获取可用方案
    const data = await apiCall('contract_plans', { hitman_id: hitmanId, contract_index: contractIndex });
    if (!data) return;

    const plans = data.extra?.plans || [];
    let html = '<p style="margin-bottom:12px;color:var(--text-secondary);">选择执行方案（Lv.3解锁）：</p>';

    // 标准方案
    html += `
        <div class="candidate-card" onclick="executeAssign(${contractIndex}, ${hitmanId}, null)" style="cursor:pointer;margin-bottom:6px;">
            <div><strong>标准执行</strong></div>
            <div style="font-size:12px;color:var(--text-muted);">按常规方式执行，收益正常</div>
        </div>
    `;

    plans.forEach(p => {
        const avClass = p.is_available ? '' : 'style="opacity:0.5;"';
        html += `
            <div class="candidate-card" onclick="${p.is_available ? `executeAssign(${contractIndex}, ${hitmanId}, '${p.id}')` : 'showToast(\'专长不匹配\')'}" ${avClass} style="cursor:${p.is_available ? 'pointer' : 'not-allowed'};margin-bottom:6px;">
                <div><strong>${p.name}</strong> ${p.is_available ? '<span style="color:var(--accent-green);font-size:11px;">✓ 匹配</span>' : '<span style="color:var(--text-muted);font-size:11px;">✗ 专长不匹配</span>'}</div>
                <div style="font-size:12px;color:var(--text-muted);">${p.desc}</div>
            </div>
        `;
    });

    showModal('🎯 选择方案', html);
    setLoading(false);
}

async function executeAssign(contractIndex, hitmanId, planId) {
    closeModal();
    closeModal(); // 关闭方案选择 + 契约板
    closeModal();
    const data = await apiCall('assign_contract', {
        contract_index: contractIndex,
        hitman_id: hitmanId,
        plan_id: planId,
    });
    if (!data) return;

    updateStats(data.state);
    appendNarrative(data.narrative, 'narrative');

    // 主线剧情
    if (data.extra?.main_story) {
        setTimeout(() => showMainStoryModal(data.extra.main_story), 300);
    }


    // 挖角弹窗
    const evt = data.extra?.event;
    if (evt?.poached) {
        showModal('⚠️ 杀手被挖', (evt.poached.name || evt.poached) + ' 被竞争对手挖走了！<br><br><button class="btn" onclick="closeModal()">确定</button>');
    }

    if (data.state.game_over) {
        appendNarrative('☠️ 游戏结束。这座城市的暗面永远在吞噬弱者。', 'game-over');
        disableGameButtons();
    }
    setLoading(false);
}

// --- 招募 ---
async function handleRecruit() {
    modalState = 'recruit';
    const data = await apiCall('recruit');
    if (!data) return;

    if (data.error) {
        appendNarrative(data.error, 'system');
        closeModal();
        return;
    }

    const candidates = data.extra?.candidates || [];
    let html = '<p style="margin-bottom:12px;color:var(--text-secondary);">今天来应聘的杀手：</p>';

    candidates.forEach((c, idx) => {
        html += `
            <div class="candidate-card" onclick="handleHire(${idx})">
                <div class="cand-name">
                    ${c.name}
                    <span style="font-size:12px;color:var(--text-muted);font-weight:400;">
                        ${c.specialty}
                    </span>
                </div>
                <div class="cand-stats">
                    <span>⚔️ 战力 ${c.skill}/5</span>
                    <span>❤️ 忠诚 ${c.loyalty}/10</span>
                    <span>📊 抽成 ${Math.round((c.cut||0.2)*100)}%</span>
                </div>
                <div class="cand-cost">
                    💸 招募费：${formatMoney(c.recruitment_cost)}
                </div>
            </div>
        `;
    });

    showModal('👤 招募新杀手', html);
    setLoading(false);
}

async function handleHire(candidateIndex) {
    closeModal();
    const data = await apiCall('hire', { candidate_index: candidateIndex });
    if (!data) return;

    if (data.extra?.hired === false) {
        appendNarrative(data.narrative, 'system');
    } else {
        updateStats(data.state);
        appendNarrative(data.narrative, 'narrative');
    }
    setLoading(false);
}

// --- 解雇杀手 ---
function handleFireHitman(hitmanId) {
    if (!confirm('确定要解雇这名杀手吗？')) return;
    apiCallAndRefresh('fire', { hitman_id: hitmanId });
}

// --- 发奖金提升忠诚 ---
async function handleBoostLoyal(hitmanId) {
    if (!confirm('给这名杀手发 ¥5,000 奖金提升忠诚度？（消耗1AP）')) return;
    dom.hitmanDetail.classList.add('hidden');
    const data = await apiCall('boost_loyal', { hitman_id: hitmanId });
    if (!data) return;
    updateStats(data.state);
    appendNarrative(data.narrative, 'system');
    setLoading(false);
}

// --- 装备/卸下武器 ---
async function doEquipWeapon(hitmanId, weaponId) {
    dom.hitmanDetail.classList.add('hidden');
    const data = await apiCall('equip_weapon', { hitman_id: hitmanId, weapon_id: weaponId });
    if (!data) return;
    updateStats(data.state);
    appendNarrative(data.narrative, 'system');
    renderHitmen(data.state.hitmen);
}

async function doUnequipWeapon(hitmanId) {
    dom.hitmanDetail.classList.add('hidden');
    const data = await apiCall('unequip_weapon', { hitman_id: hitmanId });
    if (!data) return;
    updateStats(data.state);
    appendNarrative(data.narrative, 'system');
    renderHitmen(data.state.hitmen);
}

// --- 结束今天 ---
async function handleEndDay() {
    const data = await apiCall('end_day');
    if (!data) return;

    updateStats(data.state);
    appendNarrative(data.narrative, 'narrative');

    // 街头偶遇
    const enc = data.extra?.encounter;
    if (enc && enc.name) {
        const canAfford = data.state.funds >= enc.cost && data.state.ap > 0;
        showModal('✨ 街头偶遇',
            '你在街头遇到了一个有意思的人：<br><br>' +
            '<b>' + enc.name + '</b>(' + enc.specialty + '，战力' + enc.skill + ')<br>' +
            '招募费用：¥' + enc.cost + '<br><br>' +
            (canAfford
                ? '<button class="btn btn-primary" onclick="doPickupEncounter()" style="margin-right:8px">❤ 招募</button>'
                : '<span style="color:#f87171;">' + (data.state.funds < enc.cost ? '资金不足' : '行动力不足') + '</span>'
            ) +
            '<button class="btn" onclick="closeModal()">❌ 忽略</button>'
        );
    }

    // 组织升级
    if (data.extra?.upgrade) {
        const up = data.extra.upgrade;
        appendNarrative(`⬆️ 组织晋升！${up.new_name}（Lv.${up.new_level}）`, 'event');
    }

    // 主线剧情
    if (data.extra?.main_story) {
        setTimeout(() => showMainStoryModal(data.extra.main_story), 500);
    }

    if (data.state.game_over) {
        appendNarrative('☠️ 游戏结束。这座城市又吞掉了一个组织。', 'game-over');
        disableGameButtons();
    }
    setLoading(false);
}

async function doPickupEncounter() {
    closeModal();
    const data = await apiCall('pickup');
    if (!data) return;
    updateStats(data.state);
    appendNarrative(data.narrative, 'narrative');
}

async function handleSave() {
    const slot = 1;
    try {
        const saveData = JSON.stringify(STATE);
        localStorage.setItem('killer_boss_save_' + slot, saveData);
        localStorage.setItem('killer_boss_save_session_' + slot, SESSION_ID);
        appendNarrative('\u{1F4BE} \u5B58\u6863\u5DF2\u4FDD\u5B58\uFF08localStorage\uFF09', 'narrative');
        showToast('\u5B58\u6863\u6210\u529F \u2705');
    } catch(e) {
        appendNarrative('\u26A0\uFE0F \u5B58\u6863\u5931\u8D25\uFF1A' + e.message, 'system');
    }
    await apiCall('save', { slot });
    setLoading(false);
}

async function handleLoad() {
    const slot = 1;
    const saved = localStorage.getItem('killer_boss_save_' + slot);
    if (saved) {
        try {
            const savedState = JSON.parse(saved);
            if (savedState && savedState.hitmen) {
                STATE = savedState;
                gameStarted = true;
                updateStats(savedState);
                dom.startScreen.classList.add('hidden');
                dom.gameUI.classList.remove('hidden');
                dom.btnStart.disabled = false;
                appendNarrative('\u{1F4C2} \u4ECE\u672C\u5730\u8BFB\u53D6\u5B58\u6863\u6210\u529F', 'narrative');
                showToast('\u8BFB\u6863\u6210\u529F \u2705');
                setLoading(false);
                return;
            }
        } catch(e) {
            appendNarrative('\u26A0\uFE0F \u8BFB\u6863\u5931\u8D25\uFF1A' + e.message, 'system');
        }
    }
    const data = await apiCall('load', { slot });
    if (data) {
        updateUI(data.state, data.narrative);
    } else {
        showToast('\u6CA1\u6709\u627E\u5230\u5B58\u6863 \u274C');
    }
    setLoading(false);
}


