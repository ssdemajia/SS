import re


class CodeBuilder:
    """
    将文本变为python函数
    """
    indent_step = 4  # 缩进长度

    def __init__(self, indent=0):
        self.code = []
        self.indent_level = indent

    def add_line(self, line):
        self.code.extend([" " * self.indent_level, line, '\n'])

    def indent(self):
        """
        增加当前的缩进长度
        """
        self.indent_level += self.indent_step

    def dedent(self):
        """
        减少当前缩进
        """
        self.indent_level -= self.indent_step

    def add_section(self):
        """
        新的代码段 增加一个子CodeBuilder来构建这个代码段的代码
        """
        section = CodeBuilder(self.indent_level)
        self.code.append(section)
        return section

    def __str__(self):
        """
        将code拼接后转为字符串
        """
        return "".join(str(c) for c in self.code)

    def get_globals(self):
        """
        执行字符串代码，得到全局变量，这个全局变量就包括我们的渲染函数
        :return:
        """
        assert self.indent_level == 0
        python_source = str(self)
        global_namespace = {}
        exec(python_source, global_namespace)
        return global_namespace


class Render:
    """将模板文本编译成"""
    def __init__(self, text: str, *contexts: dict):
        self.context = {}
        for context in contexts:
            self.context.update(context)
        self.all_vars = set()
        self.loop_vars = set()
        self.text = text

    def compiler(self):
        buffered = []

        def flush_output():
            """
            将buffered中的元素合并为一个extent
            :return:
            """
            if len(buffered) == 1:
                code.add_line("append_result(%s)" % buffered[0])
            elif len(buffered) > 1:
                code.add_line("extend_result([%s])" % ",".join(buffered))
            del buffered[:]

        code = CodeBuilder()
        code.add_line("def render_function(context, do_dots):")
        code.indent()
        vars_code = code.add_section()
        contexts_code = code.add_section()
        code.add_line("result = []")
        code.add_line("append_result = result.append")
        code.add_line("extend_result = result.extend")
        code.add_line("to_str = str")
        ops_stack = []
        pattern = r"(?s)({{.*?}}|{%.*?%}|{#.*?#})"
        tokens = re.split(pattern, self.text)
        for token in tokens:
            if token.startswith("{#"):  # {# #} 表示注释
                continue
            elif token.startswith("{{"):  # {{ a + b }} 形式
                expr = self.expression_code(token[2: -2].strip())
                buffered.append("to_str(%s)" % expr)
            elif token.startswith("{%"):  # {% for i in obj %} 形式
                flush_output()
                words = token[2:-2].strip().split()
                if words[0] == 'if':  # {% if a.is_true %}形式
                    if len(words) != 2:
                        self.syntax_error("if expression error")
                    ops_stack.append('if')
                    code.add_line("if %s:" % str(self.expression_code(words[1])))
                    code.indent()

                elif words[0] == 'for':
                    if len(words) != 4 or words[2] != 'in':
                        self.syntax_error("for expression error")
                    ops_stack.append('for')
                    self.variable(words[1], self.loop_vars)
                    code.add_line("for c_%s in %s:" % (words[1], self.expression_code(words[3])))
                    code.indent()

                elif words[0].startswith("end"):
                    if len(words) != 1:
                        self.syntax_error("end expression error")
                    end_what = words[0][3:]
                    if not ops_stack:  # 当ops_stack 为空时，empty list
                        self.syntax_error("too many ends")
                    start_what = ops_stack.pop()
                    if start_what != end_what:
                        self.syntax_error("mismatch tag")
                    code.dedent()
                else:
                    self.syntax_error("don't understand tag")
            else:
                if token:
                    buffered.append(repr(token))
        flush_output()
        for var_name in self.all_vars - self.loop_vars:
            vars_code.add_line("c_{var} = context['{var}']".format(var=var_name))
        for var_name in self.context:
            contexts_code.add_line("c_{var} = context['{var}']".format(var=var_name))
        code.add_line("return ''.join(result)")
        code.dedent()
        self.render_function = code.get_globals()['render_function']

    def variable(self, name, vars_set):
        """
        将一个加入变量集合中，之后需要提前声明变量到编译的python中
        :param name:
        :param vars_set:
        :return:
        """
        if not re.match(r"[_a-zA-Z][_a-zA-Z0-9]", name):
            self.syntax_error("Not a valid name")
        vars_set.add(name)

    def syntax_error(self, msg):
        print(msg)

    def expression_code(self, expression):
        """
        目前只能得到变量的值
        todo 将表达式计算出来结果 a + b 计算出结果返回
        :param expression: 一个表达式
        :return:
        """
        if '|' in expression:
            exprs = expression.split('|')
            self.variable(exprs[0], self.all_vars)
            code = "c_%s(c_%s)" % (exprs[1], exprs[0])
            for expr in exprs[2:]:
                code = "c_%s(%s)" % (expr, code)
        elif '.' in expression:
            dots = expression.split(".")
            code = self.expression_code(dots[0])
            args = ','.join(repr(d) for d in dots[1:])
            code = "do_dots(%s, %s)" % (code, args)
        else:
            self.variable(expression, self.all_vars)
            code = 'c_'+expression
        return code

    def do_dots(self, value, *dots):
        """
        表达式x.y.z编译成do_dots(x, 'y', 'z'), 先执行x.y得到value然后value.z
        :param value:
        :param dots:
        :return:
        """
        for dot in dots:
            try:
                value = getattr(value, dot)
            except AttributeError:
                value = value[dot]
            if callable(value):
                value = value()
        return value

    def render(self, context=None):
        render_context = dict(self.context)
        if context:
            render_context.update(context)
        return self.render_function(render_context, self.do_dots)


if __name__ == '__main__':
    template1 = """
        <h1> Hello {{ name|upper }} !</h1>"""

    template2 = """
        <h1>Hello {{name|upper}}!</h1>
        {% if obj.isTrue %}
           <p> Yes~ </p>
        {% endif %}"""
    template3 = '''
            <h1>Hello {{name|upper}}!</h1>
            {% for topic in topics %}
                <p>You are interested in {{topic}}.</p>
            {% endfor %}
            '''
    r = Render(template2, {'upper': str.upper})  # 这一步将模板变为python函数
    r.compiler()
    html = r.render({'name': 'ss', 'topics': ['Python', 'Geometry', 'Juggling'], 'obj': {'isTrue': False}})   # 参数将作为编译生成的模板函数的参数
    print(html)
