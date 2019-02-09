%!TEX root = prova.tex

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% OMR enabled exam
% LaTeX Class
% Version 1.0 (7/2/19)
%
% Author:
% Luca Di Gaspero (luca.digaspero@uniud.it)
%
% License:
% CC BY-NC-SA 3.0 (http://creativecommons.org/licenses/by-nc-sa/3.0/)
%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

%----------------------------------------------------------------------------------------
%	CLASS DEFINITION
%----------------------------------------------------------------------------------------

\NeedsTeXFormat{LaTeX2e}

\ProvidesClass{example}[2019/02/07 OMR Exam Class v1.0] % Class information printed in the log during every compilation

\ProcessOptions\relax % Process class options

\LoadClass[a4paper,10pt]{exam} % Load the primary class with set options

%\@ifundefined{classtoggle} % Check that the \classtoggle has been defined, i.e. one of the two required class options above has been specified
%{\ClassError{example}{You have not used one of the required options}{You must specify one of the class options defined in the template file.}} % If one of the options has not been specified, quit with an error to that effect
%{} % Otherwise do nothing

%----------------------------------------------------------------------------------------
%	REQUIRED PACKAGES
%----------------------------------------------------------------------------------------

\usepackage{tikz}
\usepackage{tikzpagenodes} % for tikz measures relative to page elements
\usetikzlibrary{shapes.misc}
\usetikzlibrary{calc}
\usepackage{amsmath, amssymb}
\usepackage[a4paper, %textwidth=12.5cm, 
  top=4cm, 
  headheight=2.5cm, 
  bottom=3.5cm, 
  left=1.5cm, 
  right=6.5cm,
  marginparsep=0.5cm, marginparwidth=4.5cm]{geometry}
\usepackage{bophook}
\usepackage[nolinks]{qrcode}
\usepackage{environ}
\usepackage{xifthen}
\usepackage{calc}

\pagestyle{empty}

\tikzset{cross/.style={cross out, rotate=45, draw=black, minimum size=2*(#1-\pgflinewidth), inner sep=0pt, outer sep=0pt},
cross/.default={0.25cm}}
\tikzset{rectangle/.style={fill=black, minimum size=2*(#1-\pgflinewidth), inner sep=0pt, outer sep=0pt},
rectangle/.default={0.2cm}}

\newboolean{student@defined}
\DeclareRobustCommand{\thestudent}{\ClassError{omrexam}{No \noexpand\student given}{You should provide a \noexpand\student{<Matriculation Number>}{<Student Name>}{} command in the document preamble}}
\DeclareRobustCommand{\thematriculationno}{\ClassError{omrexam}{No \noexpand\student given}{You should provide a \noexpand\student{<Matriculation Number>}{<Student Name>} command in the document preamble}}
\DeclareRobustCommand{\student}[2]{\renewcommand\thematriculationno{#1}\renewcommand\thestudent{#2}\setboolean{student@defined}{true}}
\newboolean{examname@defined}
\DeclareRobustCommand{\theexam}{\ClassError{omrexam}{No \noexpand\examname given}{You should provide a \noexpand\examname{<Exam Name>} command in the document preamble}}
\DeclareRobustCommand{\examname}[1]{\renewcommand\theexam{#1}\setboolean{examname@defined}{true}}
% In case there is no solution, the qrcode is used only as a reference marker
\newcommand\thesolution{None}
\DeclareRobustCommand{\solution}[1]{\renewcommand\thesolution{#1}}

\newcounter{total@questions}
\newcounter{current@question@start}
\newcommand*{\ExtractCoordinates}[3]{\path (#1); \pgfgetlastxy{#2}{#3}}%
\newcommand*{\XDistance}[2]{\path (#1); \pgfgetlastxy{\XCoordA}{\YCoord}; \path (#2); \pgfgetlastxy{\XCoordB}{\YCoord}; \pgfmathsetmacro{\DistanceX}{\XCoordB - \XCoordA}}%
\newcommand*{\YDistance}[2]{\path (#1); \pgfgetlastxy{\XCoord}{\YCoordA}; \path (#2); \pgfgetlastxy{\XCoord}{\YCoordB}; \pgfmathsetmacro{\DistanceY}{\XCoordB - \XCoordA}}%

\DeclareRobustCommand{\omr@markers}{%
  \ifthenelse{\boolean{student@defined} \AND \boolean{examname@defined}}{%
  \begin{tikzpicture}[remember picture,overlay]        
%    \draw [gray]
%        (current page marginpar area.south west)
%        rectangle
%        (current page marginpar area.north east);

    \draw 
        (current page.north west)
        node [below right, text width=2cm, xshift=1cm, yshift=-1cm] (TL) {X};
    
    \draw 
        (current page.south east)
        node[above left, align=right, text width=2cm, xshift=-1cm, yshift=1cm] (BR) {X};

    \XDistance{current page.north west}{current page.south east};
    \ExtractCoordinates{current page marginpar area.north west}{\OMR@TopLeft@XCoord}{\OMR@TopLeft@YCoord};
    \pgfmathtruncatemacro{\OMR@TopLeft@XCoord}{\OMR@TopLeft@XCoord / \DistanceX * 100.0 + 0.5};
    \pgfmathtruncatemacro{\OMR@TopLeft@YCoord}{-\OMR@TopLeft@YCoord / \DistanceX * 100.0 + 0.5};
    \ExtractCoordinates{current page marginpar area.south east}{\OMR@BottomRight@XCoord}{\OMR@BottomRight@YCoord};
    \pgfmathtruncatemacro{\OMR@BottomRight@XCoord}{\OMR@BottomRight@XCoord / \DistanceX * 100.0 + 0.5};
    \pgfmathtruncatemacro{\OMR@BottomRight@YCoord}{-\OMR@BottomRight@YCoord / \DistanceX * 100.0 + 0.5};   
    \ExtractCoordinates{current page.north west}{\Page@TopLeft@XCoord}{\Page@TopLeft@YCoord};
    \ExtractCoordinates{current page.south east}{\Page@BottomRight@XCoord}{\Page@BottomRight@YCoord};
    % The distance between the corner of the top left QRCode and the bottom right QRCode expressed in mm
    \pgfmathtruncatemacro{\QR@Diagonal}{0.351459804 * veclen(\Page@TopLeft@XCoord + 1cm - \Page@BottomRight@XCoord + 1cm, \Page@TopLeft@YCoord - 1cm - \Page@BottomRight@YCoord - 1cm) + 0.5};
    \def\OMR@Sizes{(\OMR@TopLeft@XCoord, \OMR@TopLeft@YCoord)-(\OMR@BottomRight@XCoord, \OMR@BottomRight@YCoord)/\QR@Diagonal}
    \draw
        (current page header area.north west)
        node[below right, xshift=2cm] {\parbox{\textwidth + \marginparwidth - 1.5cm}{{\Large \theexam} \\ \@date \\ \thematriculationno, \thestudent}};  
    \draw 
        (current page.north west)
        node[below right, text width=2cm, xshift=1cm, yshift=-1cm] {\qrcode[height=2cm]{\thematriculationno,\@date,[\thesolution]}};           
    \draw 
        (current page.south east)
        node[above left, text width=2cm, xshift=-1cm, yshift=1cm] {%         
        \ifthenelse{\cnttest{\thecurrent@question@start}{<=}{\thetotal@questions}}{%
          \qrcode[height=2cm]{\OMR@Sizes,\thepage,\thecurrent@question@start-\thetotal@questions}
        }{\qrcode[height=2cm]{\OMR@Sizes,\thepage}}
        };
  \end{tikzpicture}  
  }{}
}

% Check that \student and \exam have been set
\AtBeginDocument{
\phantom{\thestudent, \theexam}
\setcounter{current@question@start}{1}
}
\AtBeginPage{
\omr@markers
\setcounter{current@question@start}{\numexpr\thetotal@questions + 1\relax}
}
%
\newlength\measure@omrtikzw
\newlength\measure@ormtikzwdifference
\newsavebox{\measure@omrchoices}
%
\NewEnviron{checkomrchoiceswidth}[1]{%  
  \savebox{\measure@omrchoices}{\BODY}
  \setlength{\measure@omrtikzw}{\wd\measure@omrchoices}  
  \ifthenelse{\lengthtest{\measure@omrtikzw > #1}}{%
    \setlength{\measure@ormtikzwdifference}{\measure@omrtikzw - #1}
    \errmessage{The set of OMR choices is larger than the allowed space by \the\measure@ormtikzwdifference, you should enlarge the margin par width to fit it}
  }{\BODY}  
  \stepcounter{total@questions}
}

\newcounter{omranswers}
\newcommand{\omrchoices}[1]{%
\marginpar{
\begin{checkomrchoiceswidth}{\marginparwidth}
\begin{tikzpicture}
\foreach \position in {1, ..., #1} {
\setcounter{omranswers}{\position}
\node [draw, ultra thick, fill, circle, inner sep=2pt, minimum size=13pt, color=gray!50] at (-1, 0) {\phantom{A}};
\node [draw, ultra thick, circle, inner sep=2pt, minimum size=13pt, color=gray!50] at ($({0.75 * \position}, 0) - (1, 0)$) {\Alph{omranswers}};
};
\end{tikzpicture}
\end{checkomrchoiceswidth}
}
}

\endinput
