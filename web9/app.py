from flask import Flask
from flask import render_template
from flask import redirect
from flask import url_for
from flask import request
from flask import abort
from flask import flash
from flask import session
from my_log import log

from models import User
from models import Blog
from models import Comment


app = Flask(__name__)
app.secret_key = 'peng'
not_admin = 2


# 通过 session 来获取当前登录的用户
def current_user():
    try:
        user_id = session['user_id']
        user = User.query.filter_by(id=user_id).first()
        return user
    except KeyError:
        return None


@app.route('/')
def index():
    return redirect(url_for('login_view'))


# 显示登录界面的函数  GET
@app.route('/login')
def login_view():
    return render_template('login.html')


# 处理登录请求  POST
@app.route('/login', methods=['POST'])
def login():
    u = User(request.form)
    user = User.query.filter_by(username=u.username).first()
    log(user)
    if u.validate(user):
        log("用户登录成功")
        session['user_id'] = user.id
        r = redirect(url_for('timeline_view', username=user.username))
        return r
    else:
        log("用户登录失败", user)
        flash('登录失败')
        return redirect(url_for('login_view'))


# 处理登出的请求 GET
@app.route('/logout', methods=['GET'])
def logout():
    user_now = current_user()
    if user_now is None:
        return redirect(url_for('login_view'))
    else:
        session.pop('user_id')
        return redirect(url_for('login_view'))


@app.route('/register')
def register_view():
    return render_template('register.html')


# 处理注册的请求  POST
@app.route('/register', methods=['POST'])
def register():
    u = User(request.form)
    if u.valid():
        log("用户注册成功")
        flash('注册成功')
        # 保存到数据库
        u.save()
        return redirect(url_for('login_view'))
    else:
        log('注册失败', request.form)
        flash('注册失败')
        return redirect(url_for('register_view'))


# 显示某个用户的主页  GET
@app.route('/timeline/<username>')
def timeline_view(username):
    u = User.query.filter_by(username=username).first()
    # 为了给模板传参，确定是否为当前用户，就能判断是否显示欢迎语
    user_now = current_user()
    # uu = User.query.filter_by(id=100).all()
    # log('changdu',len(uu)) 测试没有的话就会返回0的长度
    log(u)
    if u is None:
        # 找不到就返回 404, 这是 flask 的默认 404 用法
        abort(404)
    if user_now is None:
        abort(401)
    else:
        blogs = u.blogs
        blogs.sort(key=lambda t: t.created_time, reverse=True)
        log(blogs)
        return render_template('timeline.html', blogs=blogs, user_now=user_now, username=username)


# 显示 博客 的页面  GET
@app.route('/blog/<blog_id>', methods=['GET'])
def blog_view(blog_id):
    user_now = current_user()
    if user_now is None:
        return redirect(url_for('login_view'))
    else:
        blog = Blog.query.filter_by(id=blog_id).first()
        # release_time = local_time(blog.created_time)
        comments = blog.comments
        comments.sort(key=lambda t: t.created_time, reverse=True)
        log('看博客')
        return render_template('blog_view.html', user_now=user_now, comments=comments, blog=blog)


# 显示 写博客 的页面 GET
@app.route('/blog/add', methods=['GET'])
def blog_add_view():
    user_now = current_user()
    log('写博客')
    if user_now is None:
        return redirect(url_for('login_view'))
    else:
        return render_template('blog_add.html', user_now=user_now)


# 处理 写博客 的请求 POST
@app.route('/blog/add', methods=['POST'])
def blog_add():
    user_now = current_user()
    if user_now is None:
        return redirect(url_for('login_view'))
    else:
        blog = Blog(request.form)
        blog.user = user_now
        blog.save()
        log('发布成功')
        return redirect(url_for('timeline_view', username=user_now.username))


# 处理 发送 评论的函数  POST
@app.route('/comment/add/<blog_id>', methods=['POST'])
def comment_add(blog_id):
    user_now = current_user()
    if user_now is None:
        return redirect(url_for('login_view'))
    else:
        c = Comment(request.form)
        # 设置是谁发的
        c.sender_name = user_now.username
        c.blog = Blog.query.filter_by(id=blog_id).first()
        # 保存到数据库
        c.save()
        blog = c.blog
        blog.com_count = len(Comment.query.filter_by(blog_id=blog.id).all())
        blog.save()
        log('写评论')
        return redirect(url_for('blog_view', blog_id=blog_id))


# 显示 用户列表 的界面 GET
@app.route('/users/list')
def users_view():
    user_now = current_user()
    all_users = User.query.all()
    if user_now is None:
        return redirect(url_for('login_view'))
    else:
        log('看用户')
        return render_template('all_users.html', user_now=user_now, all_users=all_users)


# 显示 编辑用户 的界面 GET
@app.route('/user/update/<user_id>')
def user_update_view(user_id):
    u = User.query.filter_by(id=user_id).first()
    if u is None:
        abort(404)
    # 获取当前登录的用户, 如果用户没登录, 就返回 401 错误
    user_now = current_user()
    if user_now is None or user_now.role == not_admin:
        abort(401)
    else:
        return render_template('user_edit.html', user_now=user_now)


# 处理 编辑用户 的请求 POST
@app.route('/user/update/<user_id>', methods=['POST'])
def user_update(user_id):
    u = User.query.filter_by(id=user_id).first()
    if u is None:
        abort(404)
    # 获取当前登录的用户, 如果用户没登录或者用户不是这条微博的主人, 就返回 401 错误
    user_now = current_user()
    if user_now is None or user_now.role == not_admin:
        abort(401)
    else:
        if u.update(request.form):
            u.save()
        return redirect(url_for('users_view'))


# 处理 删除 用户的请求
@app.route('/user/delete/<user_id>')
def user_delete(user_id):
    u = User.query.filter_by(id=user_id).first()
    user_now = current_user()
    if user_now is None or user_now.role == not_admin:
        abort(401)
    else:
        u.delete()
        return redirect(url_for('users_view'))


# 显示 更新 博客的页面 GET
@app.route('/blog/update/<blog_id>', methods=['GET'])
def blog_update_view(blog_id):
    user_now = current_user()
    blog = Blog.query.filter_by(id=blog_id).first()
    if user_now is None:
        abort(401)
    else:
        return render_template('blog_update.html', user_now=user_now, blog=blog)


# 处理 更新 博客的请求 POST
@app.route('/blog/update/<blog_id>', methods=['POST'])
def blog_update(blog_id):
    user_now = current_user()
    blog = Blog.query.filter_by(id=blog_id).first()
    if user_now is None:
        abort(401)
    else:
        blog.update(request.form)
        blog.save()
        return redirect(url_for('blog_view', blog_id=blog_id))


# 处理 删除 博客的请求 GET
@app.route('/blog/delete/<blog_id>', methods=['GET'])
def blog_delete(blog_id):
    user_now = current_user()
    blog = Blog.query.filter_by(id=blog_id).first()
    if user_now is None:
        abort(401)
    else:
        blog.delete()
        return redirect(url_for('timeline_view', username=user_now.username))


if __name__ == '__main__':
    host, port = '0.0.0.0', 5000
    args = {
        'host': host,
        'port': port,
        'debug': True,
    }
    app.run(**args)
