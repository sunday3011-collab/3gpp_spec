#!/usr/bin/env python3
"""
OMML (Office Math Markup Language, m: namespace) -> LaTeX 转换器，纯标准库。

3GPP docx 中公式有两种形态:
  1. m:oMath / m:oMathPara (OMML, 现代公式) -> 本模块转成 $...$ LaTeX
  2. OLE 对象 (Equation.3 / Equation.DSMT4, 带EMF/WMF预览图) -> 由
     download_and_convert.py 提取为图片

覆盖的 OMML 结构 (38系列协议实际使用的子集):
  m:r, m:f, m:d, m:sSub, m:sSup, m:sSubSup, m:sPre, m:nary, m:rad,
  m:func, m:limLow, m:limUpp, m:bar, m:acc, m:groupChr, m:m (matrix),
  m:eqArr, m:phantom, m:box, m:borderBox, m:spacer, m:sSubPr 等 Pr 节点

用法:
  from omml2latex import omml_to_latex
  latex = omml_to_latex(math_elem)   # math_elem: m:oMath 的 Element
"""

import re
import xml.etree.ElementTree as ET

M_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

# ---- Unicode -> LaTeX 符号映射 (MathJax/KaTeX 均支持) ----
SYM = {
    "−": "-", "–": "-", "\u00b7": r"\cdot ", "\u22c5": r"\cdot ",
    "\u2219": r"\cdot ", "\u2022": r"\cdot ", "\u25aa": r"\cdot ",
    "\u2219": r"\cdot ", "\u2299": r"\odot ",
    "\u00d7": r"\times ", "\u2217": "*", "\u2218": r"\circ ",
    "\u2264": r"\leq ", "\u2265": r"\geq ", "\u2260": r"\neq ",
    "\u2248": r"\approx ", "\u2261": r"\equiv ", "\u226a": r"\ll ",
    "\u226b": r"\gg ", "\u221e": r"\infty ", "\u2208": r"\in ",
    "\u2209": r"\notin ", "\u2282": r"\subset ", "\u2286": r"\subseteq ",
    "\u2283": r"\supset ", "\u2287": r"\supseteq ", "\u222a": r"\cup ",
    "\u2229": r"\cap ", "\u2200": r"\forall ", "\u2203": r"\exists ",
    "\u2205": r"\emptyset ", "\u2295": r"\oplus ", "\u2297": r"\otimes ",
    "\u2213": r"\mp ", "\u00b1": r"\pm ", "\u226a": r"\ll ",
    "\u2261": r"\equiv ", "\u2192": r"\to ", "\u21d2": r"\Rightarrow ",
    "\u2194": r"\leftrightarrow ", "\u21d4": r"\Leftrightarrow ",
    "\u2211": r"\sum ", "\u220f": r"\prod ", "\u222b": r"\int ",
    "\u221a": r"\sqrt ", "\u2202": r"\partial ", "\u2211": r"\sum ",
    "\u2308": r"\lceil ", "\u2309": r"\rceil ", "\u230a": r"\lfloor ",
    "\u230b": r"\rfloor ", "\u27e8": r"\langle ", "\u27e9": r"\rangle ",
    "\u2243": r"\simeq ", "\u223c": r"\sim ", "\u223d": r"\backsim ",
    # Greek (小写)
    "\u03b1": r"\alpha ", "\u03b2": r"\beta ", "\u03b3": r"\gamma ",
    "\u03b4": r"\delta ", "\u03b5": r"\epsilon ", "\u03b6": r"\zeta ",
    "\u03b7": r"\eta ", "\u03b8": r"\theta ", "\u03b9": r"\iota ",
    "\u03ba": r"\kappa ", "\u03bb": r"\lambda ", "\u03bc": r"\mu ",
    "\u03bd": r"\nu ", "\u03be": r"\xi ", "\u03c0": r"\pi ",
    "\u03c1": r"\rho ", "\u03c3": r"\sigma ", "\u03c4": r"\tau ",
    "\u03c5": r"\upsilon ", "\u03c6": r"\phi ", "\u03c7": r"\chi ",
    "\u03c8": r"\psi ", "\u03c9": r"\omega ",
    # Greek (大写)
    "\u0393": r"\Gamma ", "\u0394": r"\Delta ", "\u0398": r"\Theta ",
    "\u039b": r"\Lambda ", "\u039e": r"\Xi ", "\u03a0": r"\Pi ",
    "\u03a3": r"\Sigma ", "\u03a5": r"\Upsilon ", "\u03a6": r"\Phi ",
    "\u03a8": r"\Psi ", "\u03a9": r"\Omega ",
    "\u03d5": r"\varphi ", "\u03f5": r"\varepsilon ",
}

# n-ary 操作符映射
NARY = {
    "\u2211": r"\sum", "\u220f": r"\prod", "\u222b": r"\int",
    "\u222c": r"\iint", "\u222d": r"\iiint", "\u222e": r"\oint",
    "\u22c3": r"\bigcup", "\u22c2": r"\bigcap", "\u2a00": r"\bigoplus",
    "\u2a01": r"\bigotimes",
}

# m:acc (accent) 字符映射
ACC = {
    "\u0302": "hat", "\u0303": "tilde", "\u0304": "bar", "\u0307": "dot",
    "\u0308": "ddot", "\u20d7": "vec", "\u2192": "overrightarrow",
    "\u23dc": "overparen", "\u23dd": "underparen",
}

# 组合变音符号 -> LaTeX 命令 (用于 m:t 文本中内联的组合符)
COMBINING = {
    0x0302: r"\hat", 0x0303: r"\tilde", 0x0304: r"\bar",
    0x0307: r"\dot", 0x0308: r"\ddot", 0x20d7: r"\vec",
}


def _local(tag):
    """'{ns}tag' -> 'tag'"""
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _conv_text(text):
    """m:t 原始文本 -> LaTeX: 符号映射 + 组合变音符号处理"""
    if not text:
        return ""
    for k, v in SYM.items():
        if k in text:
            text = text.replace(k, v)
    # 组合变音符号: "x\u0302" -> \hat{x}
    for cp, cmd in COMBINING.items():
        ch = chr(cp)
        if ch in text:
            text = re.sub(r"(\w)" + re.escape(ch), r"\\" + cmd + r"{\1}", text)
            text = text.replace(ch, "")
    return text


def _grp(s):
    """给表达式加花括号分组 (若超过单字符)"""
    s = s.strip()
    if len(s) == 1:
        return s
    return "{" + s + "}"


def _child(elem, name):
    """按 local name 找第一个子元素"""
    for c in elem:
        if _local(c.tag) == name:
            return c
    return None


def _child_all(elem, name):
    return [c for c in elem if _local(c.tag) == name]


def _content(elem):
    """转换一个容器元素 (m:e, m:num, m:den, ...) 的全部子内容"""
    return "".join(_dispatch(c) for c in elem if not _local(c.tag).endswith("Pr"))


def _dispatch(elem):
    tag = _local(elem.tag)
    fn = _DISPATCH.get(tag)
    if fn:
        return fn(elem)
    # Pr 节点 / 控制属性: 忽略
    if tag.endswith("Pr"):
        return ""
    # 其他未知容器: 递归
    return _content(elem)


# ---- 各 OMML 结构的处理函数 ----

def _do_r(elem):
    """m:r 数学 run: 拼接其中 m:t 文本"""
    out = []
    for c in elem.iter():
        if _local(c.tag) == "t" and c.tag.startswith("{%s}" % M_NS):
            out.append(_conv_text(c.text))
    return "".join(out)


def _do_t(elem):
    return _conv_text(elem.text or "")


def _do_f(elem):
    """m:f 分数"""
    num, den = _child(elem, "num"), _child(elem, "den")
    num_s = _content(num) if num is not None else ""
    den_s = _content(den) if den is not None else ""
    # m:fPr m:type: bar(默认/frac) / lin(线性) / skw / noBar
    fpr = _child(elem, "fPr")
    ftype = None
    if fpr is not None:
        t = _child(fpr, "type")
        if t is not None:
            ftype = t.get("{%s}val" % M_NS)
    if ftype == "lin":
        return "%s/%s" % (num_s, den_s)
    if ftype == "noBar":
        return "%s" % num_s
    return r"\frac{%s}{%s}" % (num_s.strip(), den_s.strip())


def _do_d(elem):
    """m:d 括号/定界符"""
    dpr = _child(elem, "dPr")
    beg, sep, end = "(", "|", ")"
    if dpr is not None:
        b = _child(dpr, "begChr")
        e = _child(dpr, "endChr")
        s = _child(dpr, "sepChr")
        if b is not None:
            beg = b.get("{%s}val" % M_NS) or ""
        if e is not None:
            end = e.get("{%s}val" % M_NS) or ""
        if s is not None:
            sep = s.get("{%s}val" % M_NS) or ""
    # 注意: 格式串已含 \left/\right 前缀, 此处映射值须为纯定界符
    LB = {"{": r"\{", "}": r"\}", "|": "|", "": "."}
    RB = {"{": r"\{", "}": r"\}", "|": "|", "": "."}
    lb = LB.get(beg, beg)
    rb = RB.get(end, end)
    inner = (r" \big" + (sep or "|") + r" ").join(
        _content(e) for e in _child_all(elem, "e"))
    return r"\left%s %s \right%s" % (lb, inner, rb)


def _do_ssub(elem):
    base = _child(elem, "e")
    sub = _child(elem, "sub")
    return "%s_{%s}" % (_content(base) if base is not None else "",
                         _content(sub) if sub is not None else "")


def _do_ssup(elem):
    base = _child(elem, "e")
    sup = _child(elem, "sup")
    return "%s^{%s}" % (_content(base) if base is not None else "",
                         _content(sup) if sup is not None else "")


def _do_ssubsup(elem):
    base = _child(elem, "e")
    sub = _child(elem, "sub")
    sup = _child(elem, "sup")
    return "%s_{%s}^{%s}" % (_content(base) if base is not None else "",
                             _content(sub) if sub is not None else "",
                             _content(sup) if sup is not None else "")


def _do_spre(elem):
    """m:sPre 前置上下标: {}_{sub}^{sup}{base}"""
    sub = _child(elem, "sub")
    sup = _child(elem, "sup")
    base = _child(elem, "e")
    return "{}_{%s}^{%s}%s" % (_content(sub) if sub is not None else "",
                               _content(sup) if sup is not None else "",
                               _content(base) if base is not None else "")


def _do_nary(elem):
    """m:nary 求和/积分等 n 元算符"""
    npr = _child(elem, "naryPr")
    chr_val = "\u222b"  # 默认 ∫
    subhide = suphide = False
    if npr is not None:
        c = _child(npr, "chr")
        if c is not None and c.get("{%s}val" % M_NS):
            chr_val = c.get("{%s}val" % M_NS)
        sh = _child(npr, "supHide")
        if sh is not None and sh.get("{%s}val" % M_NS) in ("1", "true"):
            suphide = True
        bh = _child(npr, "subHide")
        if bh is not None and bh.get("{%s}val" % M_NS) in ("1", "true"):
            subhide = True
    op = NARY.get(chr_val, chr_val)
    sub = _child(elem, "sub")
    sup = _child(elem, "sup")
    e = _child(elem, "e")
    parts = [op]
    if sub is not None and not subhide:
        parts.append("_{%s}" % _content(sub))
    if sup is not None and not suphide:
        parts.append("^{%s}" % _content(sup))
    parts.append(" " + (_content(e) if e is not None else ""))
    return "".join(parts)


def _do_rad(elem):
    """m:rad 根号"""
    deg = _child(elem, "deg")
    e = _child(elem, "e")
    body = _content(e) if e is not None else ""
    deg_s = _content(deg) if deg is not None else ""
    if deg_s.strip():
        return r"\sqrt[%s]{%s}" % (deg_s.strip(), body)
    return r"\sqrt{%s}" % body


def _do_func(elem):
    """m:func 函数名 + 参数, 如 max(...) lim(...)"""
    fname = _child(elem, "fName")
    e = _child(elem, "e")
    name = _content(fname) if fname is not None else ""
    arg = _content(e) if e is not None else ""
    known = {"max", "min", "lim", "log", "ln", "exp", "sin", "cos",
             "tan", "arg", "det", "gcd", "lcm", "sup", "inf", "mod"}
    if name.strip() in known:
        return r"\%s %s" % (name.strip(), _grp(arg))
    return "%s(%s)" % (name, arg)


def _do_limlow(elem):
    """m:limLow 正下方极限, 如 min 下标 k"""
    e = _child(elem, "e")
    lim = _child(elem, "lim")
    return r"\underset{%s}{%s}" % (_content(lim) if lim is not None else "",
                                   _content(e) if e is not None else "")


def _do_limupp(elem):
    e = _child(elem, "e")
    lim = _child(elem, "lim")
    return r"\overset{%s}{%s}" % (_content(lim) if lim is not None else "",
                                  _content(e) if e is not None else "")


def _do_bar(elem):
    e = _child(elem, "e")
    return r"\overline{%s}" % (_content(e) if e is not None else "")


def _do_acc(elem):
    """m:acc 重音符号"""
    apr = _child(elem, "accPr")
    chr_val = "\u0302"
    if apr is not None:
        c = _child(apr, "chr")
        if c is not None and c.get("{%s}val" % M_NS):
            chr_val = c.get("{%s}val" % M_NS)
    cmd = ACC.get(chr_val, "hat")
    e = _child(elem, "e")
    return r"\%s{%s}" % (cmd, _content(e) if e is not None else "")


def _do_groupchr(elem):
    """m:groupChr 花括号组 (under/overbrace)"""
    gpr = _child(elem, "groupChrPr")
    chr_val = "\u23df"  # 默认下花括号
    pos = "bot"
    if gpr is not None:
        c = _child(gpr, "chr")
        if c is not None and c.get("{%s}val" % M_NS):
            chr_val = c.get("{%s}val" % M_NS)
        p = _child(gpr, "pos")
        if p is not None:
            pos = p.get("{%s}val" % M_NS) or "bot"
    e = _child(elem, "e")
    body = _content(e) if e is not None else ""
    if chr_val in ("\u23df", "\ufe37"):  # 下花括号
        return r"\underbrace{%s}" % body
    return r"\overbrace{%s}" % body


def _do_m(elem):
    """m:m 矩阵"""
    rows = []
    for mr in _child_all(elem, "mr"):
        cells = [_content(e) for e in _child_all(mr, "e")]
        rows.append(" & ".join(cells))
    return r"\begin{matrix}" + r" \\ ".join(rows) + r"\end{matrix}"


def _do_eqarr(elem):
    """m:eqArr 方程组/多行公式"""
    lines = [_content(e) for e in _child_all(elem, "e")]
    return (r"\begin{aligned}" + r" \\ ".join(lines)
            + r"\end{aligned}")


def _do_phantom(elem):
    e = _child(elem, "e")
    return r"\phantom{%s}" % (_content(e) if e is not None else "")


def _do_box(elem):
    return _content(elem)


def _do_borderbox(elem):
    e = _child(elem, "e")
    return r"\boxed{%s}" % (_content(e) if e is not None else "")


def _do_spacer(elem):
    return " "


_DISPATCH = {
    "r": _do_r, "t": _do_t, "f": _do_f, "d": _do_d,
    "sSub": _do_ssub, "sSup": _do_ssup, "sSubSup": _do_ssubsup,
    "sPre": _do_spre, "nary": _do_nary, "rad": _do_rad, "func": _do_func,
    "limLow": _do_limlow, "limUpp": _do_limupp, "bar": _do_bar,
    "acc": _do_acc, "groupChr": _do_groupchr, "m": _do_m,
    "eqArr": _do_eqarr, "phantom": _do_phantom, "box": _do_box,
    "borderBox": _do_borderbox, "spacer": _do_spacer,
}


def omml_to_latex(math_elem):
    """m:oMath 元素 -> LaTeX 字符串 (不含 $ 定界符)"""
    s = "".join(_dispatch(c) for c in math_elem)
    # 清理: 折叠空白、去首尾空格
    s = re.sub(r"[ \t]+", " ", s).strip()
    return s


# ---- 独立测试: python3 omml2latex.py <docx> ----
if __name__ == "__main__":
    import sys
    import zipfile
    path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/phy_test/extracted/word/document.xml"
    if path.endswith(".docx"):
        with zipfile.ZipFile(path) as z:
            root = ET.fromstring(z.read("word/document.xml"))
    else:
        root = ET.parse(path).getroot()
    n = 0
    for elem in root.iter("{%s}oMath" % M_NS):
        latex = omml_to_latex(elem)
        if latex:
            print("$%s$" % latex)
            n += 1
        if n >= 40:
            break
