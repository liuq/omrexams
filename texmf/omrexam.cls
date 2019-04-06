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
  left=1.5cm, 
  right=6.5cm,
  marginparsep=0.5cm, 
  marginparwidth=4.5cm]{geometry}
\usepackage{bophook}
\usepackage[nolinks]{qrcode}
\usepackage{environ}
\usepackage{xifthen}
\usepackage{calc}
\usepackage[ocr-b]{ocr}
\usepackage{lmodern}
\usepackage[T1]{fontenc}
\usepackage[export]{adjustbox}

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

\newlength{\OMR@Size}
\setlength{\OMR@Size}{14pt}

\newlength{\OMR@BorderWidth}
\setlength{\OMR@BorderWidth}{1pt}

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
    \def\OMR@Sizes{(\OMR@TopLeft@XCoord, \OMR@TopLeft@YCoord)-(\OMR@BottomRight@XCoord, \OMR@BottomRight@YCoord)/(\QR@Width, \QR@Height)/\OMR@Diameter}
    \draw
        (current page header area.north west)
        node[below right, xshift=2cm] {\parbox{\textwidth + \marginparwidth - 1.5cm}{\theheader}};  
    \draw 
        (current page.north west)
        node[below right, text width=2cm, xshift=1cm, yshift=-1cm] {\qrcode[height=2cm]{\thematriculationno,\thedate,[\thesolution]}};          \draw
        (current page.north east)
        node[below left, rectangle, draw, fill=black, xshift=-1cm, yshift=-1cm, minimum size=0.5*\OMR@Size] {~};

    % In order to determine which are the questions in the current page
    \ifthenelse{\isundefined{\exam@numquestions}}{}{%
      \def\OMR@questions@pagelist{}
      \foreach \question in {1, ..., \exam@numquestions} {%
        \ifthenelse{\cnttest{\PgInfo@get{question@\question}}{=}{\thepage}}{
          \xdef\OMR@questions@pagelist{\question,\OMR@questions@pagelist}
        }{}
      };
      \pgfmathsetmacro\OMR@questions@currentpage@start{int(min(\OMR@questions@pagelist))}
      \pgfmathsetmacro\OMR@questions@currentpage@end{int(max(\OMR@questions@pagelist))}
      \draw 
        (current page.south east)
        node[above left, text width=2cm, xshift=-1cm, yshift=1cm] {%         
        \qrcode[height=2cm]{\OMR@Sizes,\thepage,\OMR@questions@currentpage@start-\OMR@questions@currentpage@end}%
        };
    }
    \draw
        (current page.south west)
        node[above right, rectangle, draw, fill=black, xshift=1cm, yshift=1cm, minimum size=0.5*\OMR@Size] {~};
  \end{tikzpicture}  
  }{}
} 

\newcommand*\circled[1]{\tikz[baseline=(char.base)]{%
\node[shape=circle, draw, inner sep=1pt] (char) {\footnotesize{#1}};}}
\renewcommand{\questionlabel}{\textbf{{\thequestion}.}}
\renewcommand{\choicelabel}{\textbf{\sffamily\thechoice})}

\DeclareOption{circled}{
  \renewcommand{\choicelabel}{\circled{\thechoice}}
}
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

\newcommand\OMR@markbox[1]{%
\begin{tikzpicture}[remember picture, overlay]
  \coordinate (here) at (0, 0);
  \draw (current page marginpar area.west |- here) + ($(0.0, {-0.5 * \OMR@Size})$) node [anchor=south west, align=left] {#1};
\end{tikzpicture}%
\ignorespaces%
}

\newcounter{omranswers}
\newcommand{\omrchoices}[1]{%
\OMR@markbox{
\begin{checkomrchoiceswidth}{\marginparwidth}
\raisebox{-0.5\baselineskip}{
\begin{tikzpicture}[x=\OMR@Size, y=\OMR@Size]
\foreach \position in {1, ..., #1} {%
  \setcounter{omranswers}{\position}
  \node [draw, fill=black, circle, inner sep=0pt, minimum size=\OMR@Size, text=white, font=\small] at (0, 0) {\thequestion};
  %\node [draw=black, line width=\OMR@BorderWidth, circle, inner sep=0pt, minimum size=\OMR@Size] at (0, 0) {};
  %\node [circle, inner sep=0pt, minimum size=\OMR@Size, color=gray] at ($(0, {1.25 * \OMR@Size})$) {};
  \node [circle, inner sep=0pt, minimum size=\OMR@Size, color=gray] at ($({1.25 * \position}, 1.0)$) {\small\ocr{\Alph{omranswers}}};
  \node [draw=black!50!white, line width=\OMR@BorderWidth, circle, inner sep=0pt, minimum size=\OMR@Size] at ($({1.25 * \position}, 0)$) {};
};
\end{tikzpicture}
}
\end{checkomrchoiceswidth}
}
}

% FIXME: only for testing (in order to prevent transparent background), it shoudl be removed later
%\usepackage{xcolor}
%\pagecolor[HTML]{FEFEFE}

\endinput
