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
from models import Follow

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


# 得到 粉丝id 列表
def get_fan(user_id):
    fans = Follow.query.filter_by(user_id=user_id).all()
    id_list = [x.followed_id for x in fans]
    return id_list


# 关注和粉丝计数
def fan_follow_count(user):
    user.follow_count = len(Follow.query.filter_by(user_id=user.id).all())
    user.fan_count = len(Follow.query.filter_by(followed_id=user.id).all())
    user.save()
    return True


@app.route('/')
def index():
    if current_user() is None:
        return redirect(url_for('login_view'))
    else:
        return redirect(url_for('timeline_view', username=current_user().username))


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
        # 保存到数据库
        u.save()
        session['user_id'] = u.id
        return redirect(url_for('timeline_view', username=u.username))
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
        log('看个人主页')
        u.follow_count = len(Follow.query.filter_by(user_id=u.id).all())
        u.fan_count = len(Follow.query.filter_by(followed_id=u.id).all())
        u.save()
        fans_id_list = get_fan(user_now.id)
        return render_template('timeline.html', blogs=blogs, user_now=user_now, user=u,
                               fans_id_list=fans_id_list)


# 显示 博客 的页面  GET
@app.route('/blog/<blog_id>', methods=['GET'])
def blog_view(blog_id):
    user_now = current_user()
    if user_now is None:
        return redirect(url_for('login_view'))
    else:
        blog = Blog.query.filter_by(id=blog_id).first()
        comments = blog.comments
        comments.sort(key=lambda t: t.created_time, reverse=True)
        blog_comments = []
        reply_comments = []
        for x in comments:
            if x.reply_id != 0:
                reply_comments.append(x)
            else:
                blog_comments.append(x)
        log('看博客')
        return render_template('blog_view.html', user_now=user_now, blog_comments=blog_comments, blog=blog,
                               reply_comments=reply_comments)


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
        log('看所有用户')
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
        return render_template('user_edit.html', user_now=user_now, user=u)


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


# 显示 关注列表 的界面 GET
@app.route('/follow/list/<user_id>')
def follow_view(user_id):
    user_now = current_user()
    all_follows = Follow.query.filter_by(user_id=user_id).all()
    follow_users_id = [x.followed_id for x in all_follows]
    follow_users = []
    for i in follow_users_id:
        follow_users.append(User.query.filter_by(id=i).first())
    if user_now is None:
        return redirect(url_for('login_view'))
    else:
        log('看关注用户')
        follow_users.sort(key=lambda t: t.created_time, reverse=True)
        return render_template('follow_users.html', user_now=user_now, follow_users=follow_users)


# 显示 粉丝列表 的界面 GET
@app.route('/fan/list/<user_id>')
def fan_view(user_id):
    user_now = current_user()
    all_fans = Follow.query.filter_by(followed_id=user_id).all()
    fan_users = [x.follows for x in all_fans]
    if user_now is None:
        return redirect(url_for('login_view'))
    else:
        log('看粉丝用户')
        fan_users.sort(key=lambda t: t.created_time, reverse=True)
        return render_template('fan_users.html', user_now=user_now, fan_users=fan_users)


# 处理 关注用户 的请求 GET
@app.route('/follow/<user_id>')
def follow_act(user_id):
    user_now = current_user()
    if user_now is None:
        return redirect(url_for('login_view'))
    else:
        u = User.query.filter_by(id=user_id).first()
        f = Follow()
        f.user_id = user_now.id
        f.followed_id = user_id
        f.save()
        log('关注成功')
        fan_follow_count(user_now)
        return redirect(url_for('timeline_view', username=u.username))


# 处理 取消关注 的请求 GET
@app.route('/unfollow/<user_id>')
def unfollow_act(user_id):
    user_now = current_user()
    if user_now is None:
        return redirect(url_for('login_view'))
    else:
        u = User.query.filter_by(id=user_id).first()
        f = Follow().query.filter_by(user_id=user_now.id, followed_id=user_id).first()
        f.delete()
        log('取消关注成功')
        fan_follow_count(user_now)
        return redirect(url_for('timeline_view', username=u.username))


# 显示 回复评论 的页面 GET
@app.route('/reply/add/<comment_id>')
def reply_view(comment_id):
    user_now = current_user()
    if user_now is None:
        return redirect(url_for('login_view'))
    else:
        comment = Comment.query.filter_by(id=comment_id).first()
        all_comments = Comment.query.filter_by(reply_id=comment_id).all()
        user = User.query.filter_by(username=comment.sender_name).first()
        all_comments.sort(key=lambda t: t.created_time, reverse=True)
        log('查看评论回复')
        return render_template('reply_view.html', comment=comment, user=user, all_comments=all_comments,
                               user_now=user_now)


# 处理 回复评论 的页面 POST
@app.route('/reply/add/<comment_id>', methods=['POST'])
def reply_act(comment_id):
    user_now = current_user()
    c = Comment(request.form)
    c.sender_name = user_now.username
    c.reply_id = comment_id
    comment = Comment.query.filter_by(id=comment_id).first()
    c.blog_id = comment.blog.id
    c.save()
    blog = c.blog
    blog.com_count = len(Comment.query.filter_by(blog_id=blog.id).all())
    blog.save()
    log('回复评论成功')
    return redirect(url_for('reply_view', comment_id=comment_id))


if __name__ == '__main__':
    host, port = '0.0.0.0', 5000
    args = {
        'host': host,
        'port': port,
        'debug': True,
    }
    app.run(**args)
