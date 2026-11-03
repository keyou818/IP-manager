from flask import Flask, request, redirect, url_for, render_template_string, session
import sqlite3
import ipaddress
import os

app = Flask(__name__)
# 必须设置一个 secret_key 用于加密 session
app.secret_key = 'super_secret_campus_ip_key_2024'

# 🌟 登录密码设置：您可以在这里随意修改
LOGIN_PASSWORD = "admin123"

DATABASE = 'ip_manager.db'


# 初始化数据库
def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS subnets
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  vlan_id TEXT,
                  cidr TEXT UNIQUE NOT NULL,
                  description TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS ip_records
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  ip TEXT UNIQUE NOT NULL,
                  sub_id INTEGER,
                  owner TEXT,
                  remark TEXT,
                  FOREIGN KEY(sub_id) REFERENCES subnets(id) ON DELETE SET NULL)''')
    conn.commit()
    conn.close()


# ----------------- 登录页面模板 -----------------
LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>登录 - 企业IP管理系统</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .login-card { background: white; padding: 40px; border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); width: 300px; text-align: center; }
        h2 { color: #333; margin-bottom: 20px; }
        input[type="password"] { width: 100%; padding: 10px; margin-bottom: 20px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }
        button { width: 100%; padding: 10px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; }
        button:hover { background: #0056b3; }
        .error { color: #dc3545; margin-bottom: 15px; font-size: 14px; }
    </style>
</head>
<body>
    <div class="login-card">
        <h2>🔒 系统登录</h2>
        {% if error %}<div class="error">{{ error }}</div>{% endif %}
        <form method="POST" action="/login">
            <input type="password" name="password" placeholder="请输入管理密码" required autofocus>
            <button type="submit">进入系统</button>
        </form>
    </div>
</body>
</html>
"""

# ----------------- 主系统页面模板 -----------------
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>企业简易IP管理系统</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; padding: 20px; }
        .container { max-width: 1100px; margin: auto; }
        .card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 20px; }
        h2, h3 { color: #333; margin-top: 0; }
        .flex-row { display: flex; gap: 20px; }
        .col { flex: 1; }

        .header-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;}

        .form-group { display: flex; gap: 10px; margin-bottom: 15px; }
        input[type="text"], select { padding: 8px; border: 1px solid #ccc; border-radius: 4px; flex: 1; }
        button { padding: 8px 15px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; text-decoration: none; display: inline-block;}
        button:hover { background: #0056b3; }
        .btn-danger { background: #dc3545; }
        .btn-danger:hover { background: #c82333; }
        .btn-small { padding: 4px 8px; font-size: 12px; }
        .btn-success { background: #28a745; }
        .btn-success:hover { background: #218838; }
        .btn-logout { background: #6c757d; }

        table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 14px;}
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f8f9fa; }

        .alert { padding: 10px; margin-bottom: 15px; border-radius: 4px; }
        .alert-danger { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .alert-success { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }

        .progress-bar { background: #e9ecef; border-radius: 4px; height: 20px; overflow: hidden; margin-top: 5px; display: flex;}
        .progress-fill { background: #28a745; height: 100%; transition: width 0.3s; }
        .text-muted { color: #6c757d; font-size: 12px; }

        .active-row { background-color: #e2f0d9 !important; }
    </style>
</head>
<body>
<div class="container">
    <div class="header-bar">
        <h2>🌐 企业简易IP台账管理</h2>
        <a href="/logout"><button class="btn-logout">退出登录</button></a>
    </div>

    {% if message %}
        <div class="alert alert-{{ msg_type }}">{{ message }}</div>
    {% endif %}

    <div class="flex-row">
        <div class="col card">
            <h3>📌 网段 / VLAN 列表</h3>
            <form method="POST" action="/add_subnet" class="form-group" style="flex-wrap: wrap;">
                <input type="text" name="vlan_id" placeholder="VLAN ID" style="flex: 0.5;">
                <input type="text" name="cidr" placeholder="网段 (如 192.168.1.0/24)" required>
                <input type="text" name="description" placeholder="用途备注" style="flex: 1.5;">
                <button type="submit">添加网段</button>
            </form>

            <table>
                <tr>
                    <th>VLAN</th>
                    <th>网段地址</th>
                    <th>使用情况</th>
                    <th>操作</th>
                </tr>
                {% for sub in subnets %}
                <tr class="{{ 'active-row' if current_sub_id == sub[0] else '' }}">
                    <td>{{ sub[1] or '-' }}</td>
                    <td>
                        <strong>{{ sub[2] }}</strong><br>
                        <span class="text-muted">{{ sub[3] }}</span>
                    </td>
                    <td>
                        <div class="text-muted">{{ sub[4] }} / {{ sub[5] }} (剩 {{ sub[6] }})</div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: {{ (sub[4] / sub[5] * 100) if sub[5] > 0 else 0 }}%; background: {{ '#dc3545' if sub[6] < 10 else '#28a745' }};"></div>
                        </div>
                    </td>
                    <td>
                        <a href="/?sub_id={{ sub[0] }}"><button type="button" class="btn-small btn-success">查看</button></a>
                        <form method="POST" action="/delete_subnet/{{ sub[0] }}" style="margin:0; display:inline;">
                            <button type="submit" class="btn-danger btn-small" onclick="return confirm('删除网段会连带删除其下所有IP记录，确定？')">删</button>
                        </form>
                    </td>
                </tr>
                {% else %}
                <tr><td colspan="4" style="text-align:center;">请先添加网段</td></tr>
                {% endfor %}
            </table>
        </div>
    </div>

    <div class="card">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <h3 id="list-title">
                💻 {% if current_sub %} 当前显示：{{ current_sub[2] }} {% if current_sub[1] %}(VLAN {{ current_sub[1] }}){% endif %} 的 IP 列表 {% else %} 所有登记的 IP 列表 {% endif %}
            </h3>
            <a href="/" style="text-decoration: none;" id="btn-back-all" style="display: {{ 'inline' if current_sub_id else 'none' }};">
                <button type="button" style="background: #6c757d;">返回全部列表</button>
            </a>
        </div>

        <form method="POST" action="/add_ip" class="form-group">
            <select name="sub_id" id="subnet-select" onchange="filterBySubnet(this.value)">
                <option value="">-- 查看所有网段的 IP --</option>
                {% for sub in subnets %}
                <option value="{{ sub[0] }}" {% if current_sub_id == sub[0] %}selected{% endif %}>
                    {{ sub[2] }} ({{ sub[3] }})
                </option>
                {% endfor %}
            </select>
            <input type="text" name="ip" placeholder="IP地址 (必填)" required>
            <input type="text" name="owner" placeholder="使用人/设备">
            <input type="text" name="remark" placeholder="备注">
            <button type="submit">登记</button>
        </form>

        <table id="ip-table">
            <thead>
                <tr>
                    <th>IP 地址</th>
                    <th>所属网段</th>
                    <th>使用人/设备</th>
                    <th>备注</th>
                    <th>操作</th>
                </tr>
            </thead>
            <tbody id="ip-table-body">
                {% for row in records %}
                <tr>
                    <td><strong>{{ row[1] }}</strong></td>
                    <td>{{ row[5] or '未分类' }}</td>
                    <td>{{ row[3] }}</td>
                    <td>{{ row[4] }}</td>
                    <td>
                        <form method="POST" action="/delete_ip/{{ row[0] }}" style="margin:0;">
                            <button type="submit" class="btn-danger btn-small" onclick="return confirm('确定释放该 IP 吗？')">释放</button>
                        </form>
                    </td>
                </tr>
                {% else %}
                <tr id="empty-row"><td colspan="5" style="text-align:center;">暂无记录</td></tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>

<script>
    function filterBySubnet(subId) {
        const newUrl = subId ? `/?sub_id=${subId}` : `/`;
        window.history.pushState({path: newUrl}, '', newUrl);

        const titleEl = document.getElementById('list-title');
        const btnBack = document.getElementById('btn-back-all');
        const selectEl = document.getElementById('subnet-select');

        if (subId) {
            const selectedText = selectEl.options[selectEl.selectedIndex].text;
            titleEl.innerHTML = `💻 当前显示：${selectedText} 的 IP 列表`;
            btnBack.style.display = 'inline';
        } else {
            titleEl.innerHTML = `💻 所有登记的 IP 列表`;
            btnBack.style.display = 'none';
        }

        fetch(`/api/get_ips?sub_id=${subId || ''}`)
            .then(response => response.json())
            .then(data => {
                const tbody = document.getElementById('ip-table-body');
                tbody.innerHTML = '';
                if (data.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;">该网段暂无记录</td></tr>';
                    return;
                }
                data.forEach(row => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td><strong>${row.ip}</strong></td>
                        <td>${row.cidr || '未分类'}</td>
                        <td>${row.owner || ''}</td>
                        <td>${row.remark || ''}</td>
                        <td>
                            <form method="POST" action="/delete_ip/${row.id}" style="margin:0;">
                                <button type="submit" class="btn-danger btn-small" onclick="return confirm('确定释放该 IP 吗？')">释放</button>
                            </form>
                        </td>
                    `;
                    tbody.appendChild(tr);
                });
            })
            .catch(error => console.error('获取数据失败:', error));
    }
</script>
</body>
</html>
"""


# ---------------- 以下为业务逻辑代码 ----------------

def get_subnets_with_stats():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT * FROM subnets")
    subnets = c.fetchall()
    result = []
    for sub in subnets:
        sub_id, vlan_id, cidr, desc = sub
        try:
            net = ipaddress.ip_network(cidr, strict=False)
            total_usable = net.num_addresses - 2 if net.num_addresses > 2 else net.num_addresses
            c.execute("SELECT COUNT(*) FROM ip_records WHERE sub_id = ?", (sub_id,))
            used = c.fetchone()[0]
            remain = total_usable - used
        except ValueError:
            total_usable, used, remain = 0, 0, 0
        result.append((sub_id, vlan_id, cidr, desc, used, total_usable, remain))
    conn.close()
    return result


def get_records(sub_id=None):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    query = '''SELECT ip_records.id, ip, sub_id, owner, remark, subnets.cidr 
               FROM ip_records 
               LEFT JOIN subnets ON ip_records.sub_id = subnets.id'''
    params = ()
    if sub_id:
        query += " WHERE ip_records.sub_id = ?"
        params = (sub_id,)
    query += " ORDER BY subnets.cidr, ip_records.ip"
    c.execute(query, params)
    records = c.fetchall()
    conn.close()
    return records


def get_subnet_by_id(sub_id):
    if not sub_id:
        return None
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT * FROM subnets WHERE id = ?", (sub_id,))
    sub = c.fetchone()
    conn.close()
    return sub


# 1. 登录拦截器：任何页面请求前先检查是否已登录
@app.before_request
def require_login():
    # 允许访问登录页面和登录提交接口，以及静态文件（如果有的话）
    if request.endpoint in ['login', 'static']:
        return
    # 如果 session 中没有登录状态，强制跳转到登录页
    if not session.get('logged_in'):
        return redirect(url_for('login'))


# 2. 登录页面路由
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        pwd = request.form.get('password')
        if pwd == LOGIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('index'))
        else:
            error = "密码错误，请重试！"
    return render_template_string(LOGIN_TEMPLATE, error=error)


# 3. 退出登录路由
@app.route('/logout')
def logout():
    session.pop('logged_in', None)  # 清除登录状态
    return redirect(url_for('login'))


@app.route('/')
def index():
    current_sub_id = request.args.get('sub_id', type=int)
    current_sub = get_subnet_by_id(current_sub_id) if current_sub_id else None
    return render_template_string(
        HTML_TEMPLATE,
        subnets=get_subnets_with_stats(),
        records=get_records(current_sub_id),
        current_sub_id=current_sub_id,
        current_sub=current_sub
    )


@app.route('/api/get_ips')
def api_get_ips():
    sub_id = request.args.get('sub_id', type=int)
    records = get_records(sub_id)
    result = []
    for row in records:
        result.append({
            'id': row[0],
            'ip': row[1],
            'owner': row[3],
            'remark': row[4],
            'cidr': row[5]
        })
    return result


@app.route('/add_subnet', methods=['POST'])
def add_subnet():
    vlan_id = request.form.get('vlan_id', '').strip()
    cidr = request.form.get('cidr', '').strip()
    desc = request.form.get('description', '').strip()

    try:
        ipaddress.ip_network(cidr, strict=False)
    except ValueError:
        return render_template_string(HTML_TEMPLATE, subnets=get_subnets_with_stats(), records=get_records(),
                                      message="网段格式错误，请使用 CIDR 格式", msg_type="danger")

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO subnets (vlan_id, cidr, description) VALUES (?, ?, ?)", (vlan_id, cidr, desc))
        conn.commit()
        message, msg_type = f"成功添加网段：{cidr}", "success"
    except sqlite3.IntegrityError:
        message, msg_type = f"⚠️ 网段 {cidr} 已存在！", "danger"
    finally:
        conn.close()

    return render_template_string(HTML_TEMPLATE, subnets=get_subnets_with_stats(), records=get_records(),
                                  message=message, msg_type=msg_type)


@app.route('/delete_subnet/<int:id>', methods=['POST'])
def delete_subnet(id):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("DELETE FROM ip_records WHERE sub_id = ?", (id,))
    c.execute("DELETE FROM subnets WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))


@app.route('/add_ip', methods=['POST'])
def add_ip():
    sub_id = request.form.get('sub_id')
    ip = request.form.get('ip', '').strip()
    owner = request.form.get('owner', '').strip()
    remark = request.form.get('remark', '').strip()

    try:
        ip_obj = ipaddress.ip_address(ip)
    except ValueError:
        return render_template_string(HTML_TEMPLATE, subnets=get_subnets_with_stats(), records=get_records(),
                                      message="IP 格式不正确！", msg_type="danger")

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    c.execute("SELECT cidr FROM subnets WHERE id = ?", (sub_id,))
    subnet_data = c.fetchone()
    if subnet_data:
        net = ipaddress.ip_network(subnet_data[0], strict=False)
        if ip_obj not in net:
            conn.close()
            return render_template_string(HTML_TEMPLATE, subnets=get_subnets_with_stats(), records=get_records(),
                                          message=f"⚠️ 错误：IP {ip} 不在网段 {subnet_data[0]} 内！", msg_type="danger")
    else:
        conn.close()
        return render_template_string(HTML_TEMPLATE, subnets=get_subnets_with_stats(), records=get_records(),
                                      message="⚠️ 请选择有效的所属网段！", msg_type="danger")

    try:
        c.execute("INSERT INTO ip_records (ip, sub_id, owner, remark) VALUES (?, ?, ?, ?)", (ip, sub_id, owner, remark))
        conn.commit()
        message, msg_type = f"成功登记 IP：{ip}", "success"
    except sqlite3.IntegrityError:
        c.execute("SELECT owner, remark FROM ip_records WHERE ip = ?", (ip,))
        exist = c.fetchone()
        message = f"⚠️ 冲突提醒：IP {ip} 已被占用！使用者：{exist[0] or '未知'}，备注：{exist[1] or '无'}"
        msg_type = "danger"
    finally:
        conn.close()

    return redirect(url_for('index', sub_id=sub_id) if sub_id else url_for('index'))


@app.route('/delete_ip/<int:id>', methods=['POST'])
def delete_ip(id):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("DELETE FROM ip_records WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(request.referrer or url_for('index'))


if __name__ == '__main__':
    if not os.path.exists(DATABASE):
        init_db()
    else:
        init_db()

    # 🌟 自动打开浏览器的代码
    import threading
    import webbrowser


    def open_browser():
        webbrowser.open_new("http://127.0.0.1:5000")


    # 延迟 1 秒打开，防止服务器还没启动完毕
    threading.Timer(1.0, open_browser).start()

    print("=======================================")
    print("  IP 台账管理系统已启动！")
    print("  请不要关闭此窗口，关闭即停止服务。")
    print("=======================================")
    # 打包成 exe 时，建议把 debug 设为 False
    app.run(host='0.0.0.0',debug=False, port=5000)