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

\ProvidesClass{omrexams}[2019/02/07 OMR Exam Class v1.0] % Class information printed in the log during every compilation

\ProcessOptions\relax % Process class options

\LoadClass[a4paper,10pt,oneside]{exam} % Load the primary class with set options

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
\usetikzlibrary{positioning}
\usetikzlibrary{decorations.markings}
\usepackage{amsmath, amssymb}
\usepackage[a4paper, 
  top=3.75cm, 
  headheight=2.25cm, 
  bottom=3.5cm, 
  left=1cm, 
  right=6.5cm,
  marginparsep=0.5cm, 
  marginparwidth=5cm]{geometry}
\usepackage{bophook}
\usepackage[nolinks]{qrcode}
\usepackage{environ}
\usepackage{xifthen}
\usepackage[ocr-b]{ocr}
\usepackage{lmodern}
\usepackage[T1]{fontenc}
\usepackage[export]{adjustbox}
\usepackage{newunicodechar}
\usepackage{fdsymbol}
\usepackage{listings}
\lstset{
  escapeinside={\%*}{*)},
  inputencoding=utf8
}
%\usepackage{fontspec}
\usepackage{mathspec}

\CorrectChoiceEmphasis{\bfseries\boldmath\color{red}}

\newcommand\Warning{%
 \makebox[1.4em][c]{%
 \makebox[0pt][c]{\raisebox{.1em}{\small!}}%
 \makebox[0pt][c]{\color{red}\Large$\bigtriangleup$}}}%

\newunicodechar{⚠}{\Warning}
\newunicodechar{◼}{$\blacksquare$}
\newunicodechar{▢}{$\square$}
\newunicodechar{▲}{$\blacktriangle$}
\newunicodechar{★}{$\bigstar$}
\newunicodechar{♦}{$\blacklozenge$}
\newunicodechar{♥}{$\varheartsuit$}
\newunicodechar{♦}{$\vardiamondsuit$}
\newunicodechar{♠}{$\spadesuit$}
\newunicodechar{♣}{$\clubsuit$}

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
% In case there is no header
\newcommand\theheader{}
\DeclareRobustCommand{\header}[1]{\renewcommand\theheader{#1}}
\newcommand\thedate{\@date}
\newcommand\thefooter{}
\DeclareRobustCommand{\footer}[1]{\renewcommand\thefooter{#1}}

\newlength{\OMR@Size}
\setlength{\OMR@Size}{14pt}

\newlength{\OMR@BorderWidth}
\setlength{\OMR@BorderWidth}{1pt}

\newcommand*{\ExtractCoordinates}[3]{\path (#1); \pgfgetlastxy{#2}{#3}}%
\newcommand*{\XDistance}[2]{\path (#1); \pgfgetlastxy{\XCoordA}{\YCoord}; \path (#2); \pgfgetlastxy{\XCoordB}{\YCoord}; \pgfmathsetmacro{\DistanceX}{\XCoordB - \XCoordA}}%
\newcommand*{\YDistance}[2]{\path (#1); \pgfgetlastxy{\XCoord}{\YCoordA}; \path (#2); \pgfgetlastxy{\XCoord}{\YCoordB}; \pgfmathsetmacro{\DistanceY}{\XCoordB - \XCoordA}}%

\def\PosInfo#1#2{\expandafter\gdef\csname Pos@#1\endcsname{#2}}
\def\PosInfo@get#1{\csname Pos@#1\endcsname}

\DeclareRobustCommand{\omr@markers}{%
  \ifthenelse{\boolean{student@defined} \AND \boolean{examname@defined}}{%
  \begin{tikzpicture}[remember picture,overlay]        
    \draw 
        (current page.north west)
        node [below right, text width=2cm, xshift=1cm, yshift=-1cm] (TL) {};
    
    \draw 
        (current page.south east)
        node[above left, align=right, text width=2cm, xshift=-1cm, yshift=1cm] (BR) {};
    
    
    \ExtractCoordinates{TL.north west}{\CroppedPage@TopLeft@XCoord}{\CroppedPage@TopLeft@YCoord};
    \ExtractCoordinates{BR.south east}{\CroppedPage@BottomRight@XCoord}{\CroppedPage@BottomRight@YCoord};
    % The distance between the corner of the top left QRCode and the bottom right QRCode expressed in pt
    \pgfmathtruncatemacro{\QR@Width}{\CroppedPage@BottomRight@XCoord - \CroppedPage@TopLeft@XCoord};
    \pgfmathtruncatemacro{\QR@Height}{\CroppedPage@TopLeft@YCoord - \CroppedPage@BottomRight@YCoord};

    \pgfmathsetmacro{\OMR@Diameter}{\OMR@Size}; 
     
    \ExtractCoordinates{current page marginpar area.north west}{\OMR@TopLeft@XCoord}{\OMR@TopLeft@YCoord};
    \pgfmathtruncatemacro{\OMR@TopLeft@XCoord}{(\OMR@TopLeft@XCoord - \CroppedPage@TopLeft@XCoord)};
    \pgfmathtruncatemacro{\OMR@TopLeft@YCoord}{-(\OMR@TopLeft@YCoord - \CroppedPage@TopLeft@YCoord + 1.5 * \OMR@Diameter)};
    \ExtractCoordinates{current page marginpar area.south east}{\OMR@BottomRight@XCoord}{\OMR@BottomRight@YCoord};
    \pgfmathtruncatemacro{\OMR@BottomRight@XCoord}{(\OMR@BottomRight@XCoord - \CroppedPage@TopLeft@XCoord)};
    \pgfmathtruncatemacro{\OMR@BottomRight@YCoord}{-(\OMR@BottomRight@YCoord - \CroppedPage@TopLeft@YCoord)};   

    % All distances/sizes are expressed in points
    \draw
        (current page header area.north west)
        node[below right, xshift=2.1cm] {\parbox{\textwidth + \marginparwidth - 1.5cm}{\theheader}};  
    \draw
        (current page footer area.south west)
        node[below right, yshift=0.5cm] {\parbox{\textwidth + \marginparwidth - 1.5cm}{\thefooter}};  
    \draw
        (current page header area.south east)
        node[below right, yshift=1.5cm, xshift=0.3cm, text width=\marginparwidth + 2em, rounded rectangle, fill=yellow!50!white] (WARN) {\small \Warning~ \parbox{\marginparwidth}{\textsf{\textbf{Non scrivere in quest'area! \newline Va usata solo per annerire i cerchi di risposta.}}}};
%    \node [below of=WARN] {$\Downarrow$};
    \draw [color=black, densely dotted, transform canvas={xshift=-0.4cm}] (current page marginpar area.north west) -- (current page marginpar area.south west);
    \draw [color=black, densely dotted, transform canvas={xshift=0.5cm}] (current page marginpar area.north east) -- (current page marginpar area.south east);
    \draw 
        (current page.north west)
        node[below right, text width=2cm, xshift=1cm, yshift=-1cm] {\qrcode[height=2cm]{\thematriculationno,\thesolution}};          
    \draw
        (current page.north east)
        node[below left, rectangle, draw, fill=black, xshift=-1cm, yshift=-1cm, minimum size=0.5*\OMR@Size] {~};

    \ExtractCoordinates{current page.center}{\OMR@CurrentPageCenter@XCoord}{\OMR@CurrentPageCenter@YCoord};

    % In order to determine which are the questions in the current page
    \ifthenelse{\isundefined{\exam@numquestions}}{}{%
      \def\OMR@questions@pagelist{}
      \def\OMR@questions@posylist{}
      \foreach \question in {1, ..., \exam@numquestions} {%
        \ifthenelse{\cnttest{\PgInfo@get{question@\question}}{=}{\thepage}}{
          \xdef\OMR@questions@pagelist{\question,\OMR@questions@pagelist}
          \pgfmathsetmacro\OMR@tmp{(\PosInfo@get{question@\question} - \OMR@CurrentPageCenter@YCoord + \CroppedPage@TopLeft@YCoord)}
          \xdef\OMR@questions@posylist{\OMR@tmp,\OMR@questions@posylist}
        }{}
      };    
      \ifthenelse{\equal{\OMR@questions@pagelist}{}}%
      {
        \def\OMR@Sizes{(\OMR@TopLeft@XCoord, \OMR@TopLeft@YCoord)-(\OMR@TopLeft@XCoord, \OMR@TopLeft@YCoord)/(\QR@Width, \QR@Height)/\OMR@Diameter}
        \draw 
          (current page.south east)
          node[above left, text width=2cm, xshift=-1cm, yshift=1cm] {%         
          \qrcode[height=2cm]{\OMR@Sizes,\thepage,0-0}%
          };
      }
      {
        \pgfmathsetmacro\OMR@questions@currentpage@start{int(max(0, min(\OMR@questions@pagelist)))}
        \pgfmathsetmacro\OMR@questions@currentpage@end{int(max(0, max(\OMR@questions@pagelist)))}
        \pgfmathtruncatemacro{\OMR@questions@minyposition}{min(\OMR@questions@posylist)}
        \pgfmathtruncatemacro{\OMR@questions@minyposition}{(\OMR@questions@minyposition - 1.5 * \OMR@Diameter)}
        \pgfmathtruncatemacro{\OMR@questions@maxyposition}{max(\OMR@questions@posylist)}
        \pgfmathtruncatemacro{\OMR@questions@maxyposition}{(\OMR@questions@maxyposition + 1.5 * \OMR@Diameter)}      

        \ifthenelse{\boolean{testing}}{
        \draw [blue, line width=2pt]
        (current page marginpar area.north west)
        rectangle 
        (current page marginpar area.south east);  
        }{}

  %      \def\OMR@Sizes{(\OMR@TopLeft@XCoord, \OMR@TopLeft@YCoord)-(\OMR@BottomRight@XCoord, \OMR@BottomRight@YCoord)/(\QR@Width, \QR@Height)/\OMR@Diameter}
        \def\OMR@Sizes{(\OMR@TopLeft@XCoord, \OMR@questions@minyposition)-(\OMR@BottomRight@XCoord, \OMR@questions@maxyposition)/(\QR@Width, \QR@Height)/\OMR@Diameter}
        \draw 
          (current page.south east)
          node[above left, text width=2cm, xshift=-1cm, yshift=1cm] {%         
          \qrcode[height=2cm]{\OMR@Sizes,\thepage,\OMR@questions@currentpage@start-\OMR@questions@currentpage@end}%
          };
      }
    }
    \draw
        (current page.south west)
        node[above right, rectangle, draw, fill=black, xshift=1cm, yshift=1cm, minimum size=0.5*\OMR@Size] {~};
  \end{tikzpicture}  
  }{}
} 

\newcommand*\circled[1]{\tikz[baseline=(char.base)]{%
\node[anchor=text, shape=circle, draw, inner sep=0.2pt, minimum size=1.2em] (char) {#1};}}
\renewcommand{\questionlabel}{\textbf{{\thequestion}.}}
\renewcommand{\choicelabel}{\textbf{\sffamily\thechoice})}

\DeclareOption{circled}{
  \renewcommand{\choicelabel}{\circled{\sffamily\footnotesize\thechoice}}
}
\DeclareOption{dyslexia}{\setallmainfonts{OpenDyslexic}\setmonofont{OpenDyslexicMono}\setsansfont{OpenDyslexic}}
\newboolean{testing}
%\setboolean{testing}{false}
\DeclareOption{testing}{\setboolean{testing}{true}}
\ProcessOptions\relax


% Check that \student and \exam have been set
\AtBeginDocument{
\phantom{\thestudent, \theexam}
\renewcommand{\questionshook}{%
  \setlength{\leftmargin}{0pt}%
  \setlength{\labelwidth}{-\labelsep}%
  \setlength{\itemsep}{5pt}
}
\renewcommand{\choiceshook}{%
%  \setlength{\leftmargin}{0pt}%
  \setlength{\itemsep}{0pt}
}
\setlength{\parindent}{0pt}
}
\AtBeginPage{\omr@markers}
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
}

\newcounter{omranswers}
\def\PosInfo@write#1#2{%
  \begingroup
    \edef\reserved@a{\write\@mainaux
      {\string\PosInfo{#1}{#2}}}%
    \reserved@a
  \endgroup
}

\newcommand{\omrchoices}[1]{%
\begin{checkomrchoiceswidth}{\marginparwidth}
\begin{tikzpicture}[x=\OMR@Size, y=\OMR@Size, remember picture, overlay]  
  \coordinate (here) at (0, 0);
  \draw (current page marginpar area.west |- here) + (0.25, 0) node [anchor=north west, draw, fill=black, circle, inner sep=0pt, minimum size=\OMR@Size, text=white, font=\footnotesize] {\sf\thequestion};  
  \path (current page marginpar area.west) + (0.25, 0);
  \pgfgetlastxy{\XCoord}{\YCoord};
  \edef\q@object@label{question@\arabic{question}}
  \PosInfo@write{\q@object@label}{\YCoord}
\foreach \position in {1, ..., #1} {%
  \setcounter{omranswers}{\position}
  \draw (current page marginpar area.west |- here) + ($({1.25 * \position + 0.25}, 0)$) node [anchor=north west, draw=black!50!white, line width=\OMR@BorderWidth, circle, inner sep=0pt, minimum size=\OMR@Size] {};
  \draw (current page marginpar area.west |- here) + ($({1.25 * \position + 0.25}, 1.0)$) node [anchor=north west, circle, inner sep=0pt, minimum size=\OMR@Size, color=black!50!white] {\small\ocr{\Alph{omranswers}}};
};
\end{tikzpicture}
\end{checkomrchoiceswidth}
}

% \newcounter{omranswers}
% \newcommand{\omrchoices}[1]{%
% \OMR@markbox{
%\begin{checkomrchoiceswidth}{\marginparwidth}
% \begin{tikzpicture}[x=\OMR@Size, y=\OMR@Size]  
% \foreach \position in {1, ..., #1} {%
%   \setcounter{omranswers}{\position}
%   \node [draw, fill=black, circle, inner sep=0pt, minimum size=\OMR@Size, text=white, font=\small] at (0, 0) {\thequestion};
%   %\node [draw=black, line width=\OMR@BorderWidth, circle, inner sep=0pt, minimum size=\OMR@Size] at (0, 0) {};
%   %\node [circle, inner sep=0pt, minimum size=\OMR@Size, color=gray] at ($(0, {1.25 * \OMR@Size})$) {};
%   \node [circle, inner sep=0pt, minimum size=\OMR@Size, color=gray] at ($({1.25 * \position}, 1.0)$) {\small\ocr{\Alph{omranswers}}};
%   \node [draw=black!50!white, line width=\OMR@BorderWidth, circle, inner sep=0pt, minimum size=\OMR@Size] at ($({1.25 * \position}, 0)$) {};
% };
% \end{tikzpicture}
%\end{checkomrchoiceswidth}
% }
% }

% FIXME: only for testing (in order to prevent transparent background), it shoudl be removed later
%\usepackage{xcolor}
%\pagecolor[HTML]{FEFEFE}

\endinput
