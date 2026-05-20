/**
 * 杀手组织老板模拟器 v2 — 前端逻辑
 *
 * 纯按钮操作，无文本输入框。
 * 所有动作通过 POST /api/act 与后端交互。
 */

// ============================================================
// 状态
// ============================================================

const API_BASE = window.location.origin;

let STATE = null;          // 当前游戏状态（来自后端）
let gameStarted = false;
let loading = false;
let modalState = null;     // 模态框状态: null | 'contracts' | 'recruit' | 'assign'

// ============================================================
// DOM 引用
// ============================================================

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const dom = {
    // Header
    dayBadge: $('#day-badge'),
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

const TIMEOUT_MS = 25000;

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
    if (loading) return null;
    setLoading(true);

    try {
        const resp = await fetchWithTimeout(`${API_BASE}/api/start`, {
            method: 'POST',
        });
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

        const loyaltyHearts = '❤️'.repeat(h.loyalty).padEnd(10, '🤍');

        const weaponName = h.weapon_id ? state.weapons?.find(w => w.id === h.weapon_id)?.name || '' : '';
        const lv = h.lv || 1;
        const exp = h.exp || 0;
        const needExp = lv * 50;

        card.innerHTML = `
            <div class="name">
                ${h.name}
                <span class="spec-badge">${h.specialty}</span>
            </div>
            <div class="details">
                <span>⚔️ Lv.${lv}</span>
                <span>💪 ${h.skill}</span>
                <span>💰 ${formatMoney(h.salary)}/月</span>
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
    const hasIdleHitmen = (state.hitmen || []).some(h => h.status === 'idle');

    dom.btnRecruit.disabled = !gameStarted || state.game_over || !apOk;
    dom.btnContracts.disabled = !gameStarted || state.game_over;
    dom.btnWeaponShop.disabled = !gameStarted || state.game_over;
    dom.btnTraining.disabled = !gameStarted || state.game_over || !apOk || state.hitmen.length === 0;
    dom.btnRivals.disabled = !gameStarted || state.game_over;
    dom.btnEndDay.disabled = !gameStarted || state.game_over;
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

// --- Toast 提示 ---
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
// 显示资源变化动画
// ============================================================

function showChange(element, amount) {
    if (!amount || amount === 0) return;
    const el = document.createElement('span');
    el.className = `resource-change ${amount > 0 ? 'positive' : 'negative'}`;
    el.textContent = `${amount > 0 ? '+' : ''}${amount}`;
    el.style.position = 'absolute';
    el.style.top = '-5px';
    el.style.right = '0';
    element.style.position = 'relative';
    element.appendChild(el);
    requestAnimationFrame(() => el.classList.add('show'));
    setTimeout(() => el.remove(), 1300);
}

// ============================================================
// Modal 系统
// ============================================================

function showModal(title, contentHtml) {
    dom.modalHeader.innerHTML = `<h2>${title}</h2>`;
    dom.modalBody.innerHTML = contentHtml;
    dom.modalOverlay.classList.remove('hidden');
    // Close handler
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

// --- 派遣杀手 ---
async function handleAssignContract(contractIndex) {
    modalState = 'assign';
    const hitmen = STATE?.hitmen || [];
    const idleHitmen = hitmen.filter(h => h.status === 'idle');

    if (idleHitmen.length === 0) {
        appendNarrative('没有空闲的杀手可以派遣。', 'system');
        closeModal();
        return;
    }

    const contract = STATE.contracts[contractIndex];
    let html = `<p style="margin-bottom:12px;color:var(--text-secondary);">
        契约：<strong>${contract.name}</strong>（${contract.difficulty} · ${contract.required_specialty}）
    </p>
    <p style="margin-bottom:12px;font-size:13px;color:var(--text-muted);">选择派遣的杀手：</p>`;

    // 先显示匹配专长的
    const sorted = [...idleHitmen].sort((a, b) => {
        const aMatch = a.specialty === contract.required_specialty ? -1 : 1;
        const bMatch = b.specialty === contract.required_specialty ? -1 : 1;
        return aMatch - bMatch;
    });

    sorted.forEach(h => {
        const isMatch = h.specialty === contract.required_specialty;
        html += `
            <div class="hitman-select-card" onclick="executeAssign(${contractIndex}, ${h.id})">
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

async function executeAssign(contractIndex, hitmanId) {
    closeModal();
    const data = await apiCall('assign_contract', { contract_index: contractIndex, hitman_id: hitmanId });
    if (!data) return;

    updateStats(data.state);
    appendNarrative(data.narrative, 'narrative');

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
                    <span>💰 月薪 ${formatMoney(c.salary)}</span>
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
        // 资金不足
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

// --- 装备/卸下武器 ---
async function doEquipWeapon(hitmanId, weaponId) {
    dom.hitmanDetail.classList.add('hidden');
    const data = await apiCall('equip_weapon', { hitman_id: hitmanId, weapon_id: weaponId });
    if (!data) return;
    updateStats(data.state);
    appendNarrative(data.narrative, 'system');
    renderHitmen(data.state);
}

async function doUnequipWeapon(hitmanId) {
    dom.hitmanDetail.classList.add('hidden');
    const data = await apiCall('unequip_weapon', { hitman_id: hitmanId });
    if (!data) return;
    updateStats(data.state);
    appendNarrative(data.narrative, 'system');
    renderHitmen(data.state);
}

// --- 结束今天 ---
async function handleEndDay() {
    const data = await apiCall('end_day');
    if (!data) return;

    updateStats(data.state);
    appendNarrative(data.narrative, 'narrative');

    if (data.state.game_over) {
        appendNarrative('☠️ 游戏结束。这座城市又吞掉了一个组织。', 'game-over');
        disableGameButtons();
    }
    setLoading(false);
}

// --- 重置 ---
// --- 存档/读档 ---
async function handleSave() {
    const slot = 1;
    const data = await apiCall('save', { slot });
    if (!data) return;
    let msg = data.narrative || `💾 存档已保存（第${slot}栏）`;
    appendNarrative(msg, 'narrative');
    showToast('存档成功 ✅');
    setLoading(false);
}

async function handleLoad() {
    const savesResp = await apiCall('list_saves');
    if (!savesResp) return;
    const saves = savesResp.extra?.saves || [];
    if (saves.length === 0) {
        showToast('没有找到存档 ❌');
        setLoading(false);
        return;
    }
    const slot = 1;
    const data = await apiCall('load', { slot });
    if (!data) return;
    updateUI(data.state, data.narrative);
    setLoading(false);
}

async function handleRestart() {
    dom.btnRestart.classList.add('hidden');
    await handleStart();
}

// --- 竞争对手 ---
async function handleRivals() {
    modalState = 'rivals';
    const data = await apiCall('rivals');
    if (!data) return;
    closeModal();
    const rivals = data.extra?.rivals || [];
    const idleHitmen = (data.state.hitmen || []).filter(h => h.status === 'idle');
    let html = '';
    rivals.forEach(r => {
        const hostilityBar = '🔴'.repeat(Math.ceil(r.hostile / 20)).padEnd(5, '⚪');
        html += `<div style="border:1px solid #c0392b;border-radius:8px;padding:10px;margin-bottom:8px;background:#221111;">`;
        html += `<div style="font-weight:bold;color:#e74c3c;">${r.name}</div>`;
        html += `<div style="font-size:12px;color:#888;">💪战力${r.strength} · 🏠${r.territory}街区 · ⭐声望${r.reputation}</div>`;
        html += `<div style="font-size:11px;color:#666;">敌意: ${hostilityBar}</div>`;
        if (idleHitmen.length > 0 && data.state.ap > 0) {
            html += '<div style="margin-top:4px;font-size:11px;color:#aaa;">派遣攻击:</div><div>';
            idleHitmen.forEach(h => {
                html += `<button class="btn btn-sm" onclick="doAttackRival(${r.id},${h.id})" style="margin:2px;font-size:11px;">${h.name}</button>`;
            });
            html += '</div>';
        }
        html += '</div>';
    });
    showModal('⚔️ 竞争对手', html || '<p style="color:#888;">城里已经没有活着的对手了。</p>');
}

async function doAttackRival(rivalId, hitmanId) {
    closeModal();
    const data = await apiCall('attack_rival', { rival_id: rivalId, hitman_id: hitmanId });
    if (!data) return;
    updateStats(data.state);
    appendNarrative(data.narrative, 'system');
}

// --- 武器库 ---
async function handleWeaponShop() {
    modalState = 'weapon_shop';
    const data = await apiCall('weapon_shop');
    if (!data) return;
    closeModal();
    const weapons = data.extra?.weapons || [];
    if (weapons.length === 0) {
        appendNarrative(data.narrative, 'system');
        return;
    }
    let html = '<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">';
    weapons.forEach(w => {
        const canBuy = data.state.funds >= w.price && data.state.reputation >= w.rep_required;
        html += `<div style="border:1px solid #444;border-radius:8px;padding:10px;background:#222;">`;
        html += `<div style="font-weight:bold;">${w.name}</div>`;
        html += `<div style="font-size:12px;color:#888;">${w.type} · ${w.rarity}</div>`;
        html += `<div style="color:#d4a017;">战力+${w.bonus} · ¥${w.price}</div>`;
        html += `<div style="font-size:11px;color:#666;">需声望: ${w.rep_required}</div>`;
        if (canBuy) {
            html += `<button class="btn btn-sm" onclick="doBuyWeapon(${w.id})" style="margin-top:6px;width:100%;">购买</button>`;
        } else {
            html += `<button class="btn btn-sm" disabled style="margin-top:6px;width:100%;">${data.state.funds < w.price ? '资金不足' : '声望不够'}</button>`;
        }
        html += '</div>';
    });
    html += '</div>';
    showModal('🔫 武器库', html);
}

async function doBuyWeapon(weaponId) {
    closeModal();
    const data = await apiCall('buy_weapon', { weapon_id: weaponId });
    if (!data) return;
    updateStats(data.state);
    appendNarrative(data.narrative, 'system');
}

// --- 训练 ---
async function handleTraining() {
    modalState = 'training';
    const data = await apiCall('training');
    if (!data) return;
    closeModal();
    const options = data.extra?.training || [];
    const idleHitmen = (data.state.hitmen || []).filter(h => h.status === 'idle');
    if (options.length === 0 || idleHitmen.length === 0) {
        appendNarrative(data.narrative, 'system');
        return;
    }
    let html = '<p>选择训练项目和杀手：</p>';
    options.forEach(t => {
        const canAfford = data.state.funds >= t.cost && data.state.ap >= t.ap;
        html += `<div style="border:1px solid #444;border-radius:8px;padding:10px;margin-bottom:8px;">`;
        html += `<div style="font-weight:bold;">${t.name}</div>`;
        html += `<div style="font-size:12px;color:#888;">${t.desc}</div>`;
        html += `<div style="color:#d4a017;">¥${t.cost} · ⚡${t.ap} AP</div>`;
        if (t.min_lv) html += `<div style="font-size:11px;color:#666;">需要Lv.${t.min_lv}</div>`;
        if (!canAfford) {
            html += `<button class="btn btn-sm" disabled style="width:100%;margin-top:4px;">${data.state.funds < t.cost ? '资金不足' : 'AP不够'}</button>`;
        } else {
            idleHitmen.forEach(h => {
                const canTrain = h.lv >= (t.min_lv || 1);
                html += `<button class="btn btn-sm" onclick="doTraining('${t.id}',${h.id})" style="margin:2px;" ${!canTrain ? 'disabled' : ''}>${h.name}${!canTrain ? '(等级不够)' : ''}</button>`;
            });
        }
        html += '</div>';
    });
    showModal('💪 训练营', html);
}

async function doTraining(trainingId, hitmanId) {
    closeModal();
    const data = await apiCall('do_training', { training_id: trainingId, hitman_id: hitmanId });
    if (!data) return;
    updateStats(data.state);
    appendNarrative(data.narrative, 'system');
}

async function handleReset() {
    if (!confirm('确定要重置游戏吗？所有进度将丢失。')) return;
    const data = await apiCall('reset');
    if (!data) return;
    gameStarted = false;
    clearNarrative();
    updateStats(data.state);
    dom.startScreen.classList.remove('hidden');
    dom.gameUI.classList.add('hidden');
    setLoading(false);
}

function disableGameButtons() {
    dom.btnRecruit.disabled = true;
    dom.btnContracts.disabled = true;
    dom.btnRivals.disabled = true;
    dom.btnWeaponShop.disabled = true;
    dom.btnTraining.disabled = true;
    dom.btnEndDay.disabled = true;
    dom.btnSave.disabled = true;
    dom.btnLoad.disabled = true;
    dom.btnRestart.classList.remove('hidden');
}

// Helper: call action, update state, append narrative
async function apiCallAndRefresh(action, params) {
    const data = await apiCall(action, params);
    if (!data) return;
    updateStats(data.state);
    if (data.narrative) appendNarrative(data.narrative, 'narrative');
    setLoading(false);
}

// ============================================================
// Hitman 详细信息弹窗
// ============================================================

function showHitmanDetail(hitman, cardEl) {
    const rect = cardEl.getBoundingClientRect();
    const detail = dom.hitmanDetail;

    // 如果有已存在的解雇按钮，移除
    let fireBtnHtml = '';
    if (hitman.status === 'idle') {
        fireBtnHtml = `<button class="btn btn-danger btn-sm" onclick="handleFireHitman(${hitman.id})">🔥 解雇</button>`;
    }

    const lv = hitman.lv || 1;
    const exp = hitman.exp || 0;
    const needExp = lv * 50;
    const weapon = hitman.weapon_id ? state.weapons?.find(w => w.id === hitman.weapon_id) : null;
    const ownedWeapons = (state.weapons || []).filter(w => w.owned && !w.equipped_by);

    detail.innerHTML = `
        <div class="hd-name">${hitman.name} <span style="font-size:12px;color:#888;">Lv.${lv}</span></div>
        <div class="hd-row"><span>专长</span><span class="hd-val">${hitman.specialty}</span></div>
        <div class="hd-row"><span>战力</span><span class="hd-val">⚔️ ${hitman.skill}/10</span></div>
        <div class="hd-row"><span>忠诚</span><span class="hd-val">❤️ ${hitman.loyalty}/10</span></div>
        <div class="hd-row"><span>状态</span><span class="hd-val">${statusText(hitman.status)}</span></div>
        <div class="hd-row"><span>月薪</span><span class="hd-val">💰 ${formatMoney(hitman.salary)}</span></div>
        <div class="hd-row"><span>经验</span><span class="hd-val">${exp}/${needExp}</span></div>
        <div class="hd-row"><span>任务完成</span><span class="hd-val">${hitman.missions_completed || 0} 次</span></div>
        <div class="hd-row"><span>武器</span><span class="hd-val">${weapon ? '🔫 ' + weapon.name + '(' + weapon.rarity + ' +' + weapon.bonus + ')' : '无'}</span></div>
        <div style="margin-top:8px;padding-top:8px;border-top:1px solid var(--border);">
            ${fireBtnHtml}
            ${weapon ? `<button class="btn btn-sm" onclick="doUnequipWeapon(${hitman.id})" style="margin-top:4px;width:100%;">🔧 卸下武器</button>` : ''}
            ${ownedWeapons.length > 0 && hitman.status === 'idle' ? ownedWeapons.map(w => `<button class="btn btn-sm" onclick="doEquipWeapon(${hitman.id},${w.id})" style="margin:2px;">🔫 ${w.name}(${w.rarity})</button>`).join('') : ''}
        </div>
    `;

    detail.classList.remove('hidden');
    detail.style.left = Math.min(rect.left - 220, window.innerWidth - 240) + 'px';
    detail.style.top = Math.min(rect.top, window.innerHeight - 300) + 'px';
}

// 点击其他地方关闭详情
document.addEventListener('click', (e) => {
    if (!dom.hitmanDetail.contains(e.target) && !e.target.closest('.hitman-card')) {
        dom.hitmanDetail.classList.add('hidden');
    }
});

// ============================================================
// 工具函数
// ============================================================

function formatMoney(amount) {
    if (amount === undefined || amount === null) return '¥0';
    return '¥' + Number(amount).toLocaleString('zh-CN');
}

function setLoading(isLoading) {
    loading = isLoading;
    dom.loadingOverlay.classList.toggle('hidden', !isLoading);
    dom.loadingText.textContent = isLoading ? '枭正在收集情报……' : '';
}

// ============================================================
// 事件绑定
// ============================================================

dom.btnStart.addEventListener('click', handleStart);
dom.btnContracts.addEventListener('click', handleShowContracts);
dom.btnRecruit.addEventListener('click', handleRecruit);
dom.btnEndDay.addEventListener('click', handleEndDay);
dom.btnSave.addEventListener('click', handleSave);
dom.btnLoad.addEventListener('click', handleLoad);
dom.btnRestart.addEventListener('click', handleRestart);
dom.btnRivals.addEventListener('click', handleRivals);
dom.btnWeaponShop.addEventListener('click', handleWeaponShop);
dom.btnTraining.addEventListener('click', handleTraining);
dom.resetLink.addEventListener('click', handleReset);

// ============================================================
// 键盘快捷键
// ============================================================

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        if (!dom.modalOverlay.classList.contains('hidden')) {
            closeModal();
        }
    }
});

// ============================================================
// 初始化
// ============================================================

console.log('🗡️ 杀手组织老板模拟器 v2 loaded');
console.log('💡 使用纯按钮操作，开启你的暗面帝国吧');
