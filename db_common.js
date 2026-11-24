// db_common.js — Shared utilities, sidebar loader & cross-referenced Item Modal
(function () {
  window.DB = {
    esc(s) {
      return String(s == null ? '' : s)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
    },
    qs(name) {
      return new URLSearchParams(location.search).get(name) || '';
    },
    async loadJSON(path) {
      this._cache = this._cache || {};
      if (this._cache[path]) return this._cache[path];
      const res = await fetch(path);
      if (!res.ok) throw new Error('HTTP ' + res.status + ' for ' + path);
      const data = await res.json();
      this._cache[path] = data;
      return data;
    },
    initSidebar() {
      const root = document.getElementById('sb-root');
      if (!root) return;
      fetch('sidebar.html?v=2', { cache: 'no-cache' })
        .then(r => r.text())
        .then(html => {
          root.innerHTML = html;
          root.querySelectorAll('script').forEach(oldScript => {
            const s = document.createElement('script');
            s.textContent = oldScript.textContent;
            document.body.appendChild(s);
          });
        })
        .catch(() => console.warn('ไม่สามารถโหลด sidebar.html ได้'));
    },
    ensureModal() {
      if (document.getElementById('db-item-modal')) return;
      const div = document.createElement('div');
      div.id = 'db-item-modal';
      div.className = 'db-modal-backdrop';
      div.innerHTML = `
        <div class="db-modal" role="dialog" aria-modal="true">
          <div class="db-modal-head">
            <h3 id="db-modal-title">รายละเอียดไอเทม</h3>
            <button class="db-modal-close" onclick="DB.closeModal()">✕</button>
          </div>
          <div class="db-modal-body" id="db-modal-body"></div>
        </div>
      `;
      div.addEventListener('click', e => {
        if (e.target === div) DB.closeModal();
      });
      document.addEventListener('keydown', e => {
        if (e.key === 'Escape') DB.closeModal();
      });
      document.body.appendChild(div);
    },
    closeModal() {
      const m = document.getElementById('db-item-modal');
      if (m) m.classList.remove('open');
    },
    async openItemModal(slug, fallbackName) {
      this.ensureModal();
      const backdrop = document.getElementById('db-item-modal');
      const titleEl = document.getElementById('db-modal-title');
      const bodyEl = document.getElementById('db-modal-body');
      titleEl.textContent = fallbackName || slug;
      bodyEl.innerHTML = '<div class="loader">กำลังโหลดข้อมูล...</div>';
      backdrop.classList.add('open');

      try {
        const [searchIdx, xref] = await Promise.all([
          this.loadJSON('data/db/search_index.json'),
          this.loadJSON('data/db/item_xref.json'),
        ]);

        // Locate item in search index (match by slug or lowercase slug or name)
        const low = slug.toLowerCase();
        const found = (searchIdx.items || []).find(
          it => it.s === slug || it.s.toLowerCase() === low || it.n === slug
        );

        let fullItem = null;
        if (found) {
          const catList = await this.loadJSON(`data/db/items/${found.c}.json`);
          fullItem = catList.find(x => x.slug === found.s) || null;
        }

        const realSlug = fullItem ? fullItem.slug : (found ? found.s : slug);
        const xinfo = xref[realSlug] || xref[low] || {};

        titleEl.textContent = fullItem ? fullItem.name : (fallbackName || realSlug);

        let html = '';
        if (fullItem) {
          html += `<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px;">
            <span class="badge gold">${this.esc(fullItem.cat)}</span>
            ${fullItem.atk ? `<span class="badge red">ATK: ${this.esc(fullItem.atk)}</span>` : ''}
            ${fullItem.def ? `<span class="badge green">DEF: ${this.esc(fullItem.def)}</span>` : ''}
            <a class="badge" href="db_items.html?cat=${encodeURIComponent(fullItem.cat)}&q=${encodeURIComponent(fullItem.name)}">เปิดในหมวด ${this.esc(fullItem.cat)}</a>
          </div>`;
          if (fullItem.ds) html += `<div class="stat-th">${this.esc(fullItem.ds)}</div>`;
          if (fullItem.tds) html += `<div class="stat-en"><strong>True Stats:</strong> ${this.esc(fullItem.tds)}</div>`;
          if (fullItem.notes) html += `<div class="stat-notes"><strong>Notes:</strong> ${this.esc(fullItem.notes)}</div>`;
        } else {
          html += `<p style="color:var(--text-dim);font-size:13px;">ไม่พบรายละเอียดสเตตัสในรายการหลัก (อาจเป็นไอเทมเฉพาะเควสต์/ดรอป)</p>`;
        }

        // Monsters that drop this item
        if (xinfo.drops && xinfo.drops.length) {
          html += `<div class="xref-sec"><h4>🐉 มอนสเตอร์ที่ดรอป (${xinfo.drops.length})</h4><div class="xref-list">`;
          for (const d of xinfo.drops) {
            html += `<div class="xref-row">
              <strong>${this.esc(d.m)}</strong> ${d.lv ? `<span class="badge">Lv.${this.esc(d.lv)}</span>` : ''}
              <span style="color:var(--text-dim)"> — </span>
              <a class="item-link" href="db_zones.html?ep=${encodeURIComponent(d.ep)}&zone=${encodeURIComponent(d.zs)}">${this.esc(d.z)}${d.area ? ' [' + this.esc(d.area) + ']' : ''}</a>
            </div>`;
          }
          html += `</div></div>`;
        }

        // Blacksmith
        if (xinfo.bs && xinfo.bs.length) {
          html += `<div class="xref-sec"><h4>🔨 ช่างตีเหล็ก (Blacksmith)</h4><div class="xref-list">`;
          for (const b of xinfo.bs) {
            html += `<div class="xref-row">
              <a class="item-link" href="db_zones.html?blacksmith=${encodeURIComponent(b.bsSlug)}">${this.esc(b.town)} Blacksmith</a>
              <span class="badge gold" style="margin-left:6px">${this.esc(b.cat)}</span>
            </div>`;
          }
          html += `</div></div>`;
        }

        // Production recipes creating this item
        if (xinfo.prod && xinfo.prod.length) {
          html += `<div class="xref-sec"><h4>⚒️ สูตรการผลิต (Production)</h4><div class="xref-list">`;
          for (const p of xinfo.prod) {
            const matsHtml = (p.mats || []).map(m =>
              `<a class="item-link" href="javascript:void(0)" onclick="DB.openItemModal('${this.esc(m.slug).replace(/'/g,"\\'")}', '${this.esc(m.name).replace(/'/g,"\\'")}')">${this.esc(m.name)} x${m.qty}</a>`
            ).join(', ');
            html += `<div class="xref-row">
              <span class="badge purple">${this.esc(p.prof)} Lv.${p.lv}</span>
              <span style="margin-left:6px">ผลิตได้ x${p.qty}</span>
              <div style="margin-top:4px;color:var(--text-dim)">วัตถุดิบ: ${matsHtml}</div>
              <div style="margin-top:6px"><a class="db-btn" style="padding:4px 10px;font-size:12px" href="db_calculator.html?item=${encodeURIComponent(realSlug)}">🧮 คำนวณวัตถุดิบทั้งหมด</a></div>
            </div>`;
          }
          html += `</div></div>`;
        }

        // Used as material in production
        if (xinfo.usedIn && xinfo.usedIn.length) {
          html += `<div class="xref-sec"><h4>🧪 ใช้เป็นวัตถุดิบผลิต (${xinfo.usedIn.length} สูตร)</h4><div class="xref-list">`;
          for (const u of xinfo.usedIn.slice(0, 40)) {
            html += `<div class="xref-row">
              <a class="item-link" href="javascript:void(0)" onclick="DB.openItemModal('${this.esc(u.slug).replace(/'/g,"\\'")}', '${this.esc(u.name).replace(/'/g,"\\'")}')">${this.esc(u.name)}</a>
              <span class="badge purple" style="margin-left:6px">${this.esc(u.prof)} Lv.${u.lv}</span>
              <span style="color:var(--text-dim);margin-left:6px">(ใช้ x${u.qty})</span>
            </div>`;
          }
          if (xinfo.usedIn.length > 40) {
            html += `<div style="color:var(--text-dim);font-size:12px">...และอีก ${xinfo.usedIn.length - 40} สูตร</div>`;
          }
          html += `</div></div>`;
        }

        // Quest Rewards
        if (xinfo.quests && xinfo.quests.length) {
          html += `<div class="xref-sec"><h4>📜 รางวัลจากเควสต์</h4><div class="xref-list">`;
          for (const q of xinfo.quests) {
            html += `<div class="xref-row">
              <a class="item-link" href="db_quests.html?q=${encodeURIComponent(q.title)}">${this.esc(q.title)}</a>
              ${q.zone ? `<span style="color:var(--text-dim)"> (${this.esc(q.zone)})</span>` : ''}
            </div>`;
          }
          html += `</div></div>`;
        }

        if (!xinfo.drops && !xinfo.bs && !xinfo.prod && !xinfo.usedIn && !xinfo.quests) {
          html += `<div class="xref-sec"><p style="color:var(--text-dim);font-size:13px">ไม่มีข้อมูลดรอปหรือสูตรผลิตเพิ่มเติมในระบบ</p></div>`;
        }

        bodyEl.innerHTML = html;
      } catch (err) {
        bodyEl.innerHTML = `<div class="empty-state">ไม่สามารถโหลดข้อมูลได้: ${this.esc(err.message)}</div>`;
      }
    }
  };
})();
