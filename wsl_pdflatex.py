#!/usr/bin/env python
# coding=utf-8
#
# Copyright (C) 2019 Marc Jeanmougin
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA
#
"""
Generate Latex via a PDF using pdflatex
This is modified to use pdflatex in WSL.
"""

import os

import inkex
from inkex.base import TempDirMixin
from inkex.command import call, inkscape, ProgramRunError
from inkex import load_svg, ShapeElement, Defs

import subprocess
import sys

class PdfLatex(TempDirMixin, inkex.GenerateExtension):
    """
    Use pdflatex to generate LaTeX, this whole hack is required because
    we don't want to open a LaTeX document as a document, but as a
    generated fragment (like import, but done manually).
    """
    def add_arguments(self, pars):
        pars.add_argument('--formule', type=str, default='')
        pars.add_argument('--packages', type=str, default='')

    def generate(self):
        tex_file = os.path.join(self.tempdir, 'input.tex')
        pdf_file = os.path.join(self.tempdir, 'input.pdf') # Auto-generate by pdflatex
        svg_file = os.path.join(self.tempdir, 'output.svg')

        with open(tex_file, 'w') as fhl:
            self.write_latex(fhl)

        # get the temporary path in wsl style
        wsl_tex_file = subprocess.Popen(
                'wsl.exe -- wslpath -u {}'.format(tex_file.replace(os.sep, '/')),
                cwd=self.tempdir,
                stdout=subprocess.PIPE,
                shell=True
                ).communicate()[0].rstrip()
        if isinstance(wsl_tex_file, bytes):
            wsl_tex_file = wsl_tex_file.decode(sys.stdout.encoding or 'utf-8')

        wsl_tempdir  = subprocess.Popen(
                'wsl.exe -- wslpath -u {}'.format(self.tempdir.replace(os.sep, '/')),
                cwd=self.tempdir,
                stdout=subprocess.PIPE,
                shell=True
                ).communicate()[0].rstrip()
        if isinstance(wsl_tempdir, bytes):
            wsl_tempdir = wsl_tempdir.decode(sys.stdout.encoding or 'utf-8')

        # instant script in inkex/command.py
        process = subprocess.Popen(
            'wsl.exe -- $HOME/.local/bin/pdflatex {} -output-directory={} -halt-on-error'.format(
                wsl_tex_file,
                wsl_tempdir
                ),
            cwd=self.tempdir,
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            )
        (stdout, stderr) = process.communicate()

        #print("##############################", file=sys.stderr)
        #print(stdout.decode(), file=sys.stderr)
        #print("##############################", file=sys.stderr)
        #print(stderr.decode(), file=sys.stderr)
        #print("##############################", file=sys.stderr)

        if process.returncode != 0:
            raise ProgramRunError(f"Return Code: {process.returncode}: {stderr}\n{stdout}")
        if isinstance(stdout, bytes):
            stdout = stdout.decode(sys.stdout.encoding or 'utf-8')


        inkscape(pdf_file, export_filename=svg_file, pdf_page=1,
                 pdf_poppler=True, export_type="svg")

        if not os.path.isfile(svg_file):
            fn = os.path.basename(svg_file)
            if os.path.isfile(fn):
                # Inkscape bug detected, file got saved wrong
                svg_file = fn

        with open(svg_file, 'r') as fhl:
            svg = load_svg(fhl).getroot()
            svg.set_random_ids(backlinks=True)
            for child in svg:
                if isinstance(child, ShapeElement):
                    yield child
                elif isinstance(child, Defs):
                    for def_child in child:
                        #def_child.set_random_id()
                        self.svg.defs.append(def_child)

    def write_latex(self, stream):
        """Takes a forumle and wraps it in latex"""
        stream.write(r"""%% processed with pdflatex.py
\documentclass{minimal}
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{amsfonts}
""")
        for package in self.options.packages.split(','):
            if package:
                stream.write('\\usepackage{{{}}}\n'.format(package))
        stream.write("\n\\begin{document}\n")
        stream.write(self.options.formule)
        stream.write("\n\\end{document}\n")

if __name__ == '__main__':
    PdfLatex().run()

