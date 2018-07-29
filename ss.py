import sys
import re
import os

static_folder = 'static'
templates_folder = 'templates'


class Handler:
    def __init__(self, fn, methods, subject, pattern, app):
        self.f = fn
        self.methods = methods
        self.app = app
        self.subject = subject
        self.args = None
        self.pattern = pattern


class Request:  # Todo 增加request类表示当前的请求
    pass


class ResponseIterator:
    def __init__(self, iterable, callbacks=None, charset='utf-8'):
        self.iterator = iter(iterable)
        if callbacks is None:
            callbacks = []
        elif callable(callbacks):
            callbacks = [callbacks]
        else:
            callbacks = list(callbacks)
        iterable_close = getattr(iterable, 'close', None)
        if iterable_close:
            callbacks.insert(0, iterable_close)
        self.callbacks = callbacks
        self.charset = charset

    def __iter__(self):
        return self

    def __next__(self):
        item = next(self.iterator)
        if isinstance(item, str):
            return item.encode(self.charset)
        else:
            return item

    def close(self):
        for callback in self.callbacks:
            callback()


class Response:
    default_charset = 'utf-8'
    default_mime_type = 'text/html'
    default_status = 200

    def __init__(self, content=None, status=None, header=None, mime_type=None):
        if status is None:
            self.status = self.default_status
        else:
            self.status = status

        self.header = []
        if header:
            self.header.extend(header)
        self.header.append(('Content-Length', len(content)))    # 计算负载的长度

        if mime_type is None:   # 判断mime类型
            self.mime_type = self.default_mime_type
        else:
            self.mime_type = mime_type
        self.header.append(('Content-Type', '{mime}; charset={cs}'.format(mime=self.mime_type,
                                                                       cs=self.default_charset)))
        self.content = content

    def get_header_status(self):
        return self.status, self.header

    def get_iter(self):     # 需要返回一个可迭代对象
        # return ResponseIterator(self.content)
        return [self.content]

    def get_content(self):
        return self.content


class SS:
    def __init__(self):
        self.url_to_handler = {}
        self.url_to_handler_r = []

    def __call__(self, environ, start_response):
        self.start_response = start_response
        method = environ['REQUEST_METHOD']
        path = environ['PATH_INFO']
        handler = self.path_to_handle(path)
        try:
            if handler.args:
                result = handler.f(handler.args)    # 路径里面是/static/<filename>的形式，可以将filename作为参数放入
            else:
                result = handler.f()
        except Exception as e:
            result = self.error_handler(e)
        return self.make_response(result)

    def route(self, path, methods):
        def wrap(fn):
            self.add_to_map(fn, methods, path)      # 将此方法和他的path做映射
            return fn
        return wrap

    def add_to_map(self, fn, methods, path):
        if '<' in path and '>' in path:
            subject = path[path.find('<'):path.rfind('>')+1]    # 这里的subject还有尖括号
            path = path.replace(subject, r'(?P{subject}[^/].*?)$'.format(subject=subject))
            path = r'^' + path
            pattern = re.compile(path)
            self.url_to_handler_r.append(Handler(fn, methods, subject[1:-1], pattern, self))
        else:
            self.url_to_handler[path] = Handler(fn, methods, None, None, self)

    def path_to_handle(self, path):
        if path in self.url_to_handler:
            return self.url_to_handler[path]
        for handler in self.url_to_handler_r:
            matcher = handler.pattern.match(path)
            if matcher:
                handler.args = matcher.group(handler.subject)
                return handler

    def make_response(self, result):
        if isinstance(result, (str, bytes, list)):
            response = Response(result)
        elif isinstance(result, Response):
            response = result
        else:
            response = Response()
        status, header = response.get_header_status()
        self.start_response(status, header)
        return response.get_iter()

    def error_handler(self, error):
        err_type, err_value, err_traceback = sys.exc_info()


def read_file(filename):  # Todo 增加读取静态文件的方法
    pass


def render_html(filename, *context):
    """
    打开模板文件
    :param filename:
    :param context:
    :return:
    """

    path = os.path.join(os.getcwd(), templates_folder, filename)
    with open(path, 'rb') as fp:
        content = fp.read()
    return content


app = SS()


@app.route('/static/<filename>', 'GET')
def static(filename):
    path = os.path.join(os.getcwd(), static_folder, filename)
    with open(path, 'rb') as fp:
        content = fp.read()
    suffix = filename[filename.rfind('.')+1:]
    if suffix == 'css':
        return Response(content, 200, None, 'text/css')
    elif suffix in ('png', 'jpeg', 'gif'):
        return Response(content, 200, None, 'image/{type}'.format(type=suffix))


@app.route('/hello', 'GET')
def hello():
    return render_html('index.html')
