"""Fuzzy file path autocompletion"""

# from enum import Enum
from dataclasses import dataclass
import os
from pathlib import Path

from PyQt6.QtCore import QModelIndex, QObject, QRectF, QSize, Qt
from PyQt6.QtGui import QColor, QPainter, QTextDocument, QTextOption, QTextCursor, QFontMetrics
from PyQt6.QtWidgets import QApplication, QItemDelegate, QStyle, QStyleOptionViewItem, QStyledItemDelegate

# class ResultType(Enum):
#     FILE = "file"
#     DIRECTORY = "directory"
#     SYMLINK = "symlink"
#     OTHER = "other"

@dataclass
class Completion:
    path: Path
    display_text: str
    match_highlights: list[tuple[int, int]]
    will_create_directory: bool
    ai_suggested: bool

# This prevents the program from hanging when searching large directories, e.g. the root directory.
# Since os.walk uses breadth-first search by default, it still gives good results, as nearby directories are searched first.
# That said, there may be pathological cases where it will not find even fairly shallow matches.
# I haven't explored this in "depth" (haha) yet.
MAX_ITERATIONS = 1000
MAX_COMPLETIONS = 100

def get_completions(search: str, folder_scope: str = "/") -> list[Completion]:
    """Get file path completions based on the search input and folder scope."""
    # Normalize the search input
    search = search.strip()

    # Normalize the folder scope
    folder_scope = os.path.expanduser(folder_scope)
    if not os.path.isabs(folder_scope):
        folder_scope = os.path.join(os.getcwd(), folder_scope)
    folder_scope = os.path.normpath(folder_scope)

    # Find the deepest existing directory that exactly matches the search path
    search_crumbs = os.path.split(search)
    search_from = folder_scope
    consumed_crumbs: list[str] = []
    for crumb in search_crumbs:
        sub_path = os.path.join(search_from, crumb)
        if os.path.isdir(sub_path):
            search_from = sub_path
            consumed_crumbs.append(crumb)
        else:
            break
    # Consume the crumbs that matched exactly
    # (Could do this in the same loop, with a different type of loop, alternatively)
    search_crumbs = search_crumbs[len(consumed_crumbs):]

    # Walk the directory and find matching names
    # TODO: fuzzier matching, e.g. using difflib.get_close_matches or similar
    # TODO: sort completions by relevance, e.g. by length of the match, how many crumbs match, how in order the matches are
    completions: list[Completion] = []
    steps = 0
    for root, dirs, _files in os.walk(search_from):
        steps += 1
        if steps > MAX_ITERATIONS or len(completions) > MAX_COMPLETIONS:
            break
        for name in sorted(dirs):
            if not search_crumbs or any(crumb.lower() in name.lower() for crumb in search_crumbs):
                suggestion = os.path.join(root, name)
                # Calculating match highlights separate from actual matching is a little sus,
                # (risks differing/drifting implementations) but it's good enough for now.
                match_highlights: list[tuple[int, int]] = []
                if search_crumbs:
                    suggestion_lower = suggestion.lower()
                    for crumb in search_crumbs:
                        crumb_lower = crumb.lower()
                        start = suggestion_lower.find(crumb_lower)
                        if start != -1:
                            match_highlights.append((start, start + len(crumb)))
                completions.append(
                    Completion(
                        path=Path(suggestion),
                        display_text=suggestion,
                        match_highlights=match_highlights,
                        will_create_directory=False,
                        ai_suggested=False,
                    )
                )

    return completions[:MAX_COMPLETIONS]


class CompletionItemDelegate(QItemDelegate):
    """Custom item delegate for completion suggestions."""

    def __init__(self, parent: QObject|None=None):
        super().__init__(parent)

    def paint(self, painter: QPainter|None, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        """Override paint method to customize item appearance."""
        completion = index.data(Qt.ItemDataRole.UserRole) if index.isValid() else None
        if completion and painter:
            # Customize the appearance based on the completion type
            if completion.will_create_directory:
                painter.fillRect(option.rect, QColor(220, 255, 220))  # Light green for new directories
            elif completion.ai_suggested:
                painter.fillRect(option.rect, QColor(220, 220, 255))  # Light blue for AI suggestions

        super().paint(painter, option, index)

# void RichTextItemDelegate::paint(QPainter *painter, const QStyleOptionViewItem &inOption,
#                                  const QModelIndex &index) const {
#     QStyleOptionViewItem option = inOption;
#     initStyleOption(&option, index);

#     if (option.text.isEmpty()) {
#         // This is nothing this function is supposed to handle
#         QStyledItemDelegate::paint(painter, inOption, index);

#         return;
#     }

#     QStyle *style = option.widget ? option.widget->style() : QApplication::style();

#     QTextOption textOption;
#     textOption.setWrapMode(option.features & QStyleOptionViewItem::WrapText ? QTextOption::WordWrap
#                                                                             : QTextOption::ManualWrap);
#     textOption.setTextDirection(option.direction);

#     QTextDocument doc;
#     doc.setDefaultTextOption(textOption);
#     doc.setHtml(option.text);
#     doc.setDefaultFont(option.font);
#     doc.setDocumentMargin(0);
#     doc.setTextWidth(option.rect.width());
#     doc.adjustSize();

#     if (doc.size().width() > option.rect.width()) {
#         // Elide text
#         QTextCursor cursor(&doc);
#         cursor.movePosition(QTextCursor::End);

#         const QString elidedPostfix = "...";
#         QFontMetrics metric(option.font);
# #if QT_VERSION >= QT_VERSION_CHECK(5, 11, 0)
#         int postfixWidth = metric.horizontalAdvance(elidedPostfix);
# #else
#         int postfixWidth = metric.width(elidedPostfix);
# #endif
#         while (doc.size().width() > option.rect.width() - postfixWidth) {
#             cursor.deletePreviousChar();
#             doc.adjustSize();
#         }

#         cursor.insertText(elidedPostfix);
#     }

#     // Painting item without text (this takes care of painting e.g. the highlighted for selected
#     // or hovered over items in an ItemView)
#     option.text = QString();
#     style->drawControl(QStyle::CE_ItemViewItem, &option, painter, inOption.widget);

#     // Figure out where to render the text in order to follow the requested alignment
#     QRect textRect = style->subElementRect(QStyle::SE_ItemViewItemText, &option);
#     QSize documentSize(doc.size().width(), doc.size().height()); // Convert QSizeF to QSize
#     QRect layoutRect = QStyle::alignedRect(Qt::LayoutDirectionAuto, option.displayAlignment, documentSize, textRect);

#     painter->save();

#     // Translate the painter to the origin of the layout rectangle in order for the text to be
#     // rendered at the correct position
#     painter->translate(layoutRect.topLeft());
#     doc.drawContents(painter, textRect.translated(-textRect.topLeft()));

#     painter->restore();
# }

# QSize RichTextItemDelegate::sizeHint(const QStyleOptionViewItem &inOption, const QModelIndex &index) const {
#     QStyleOptionViewItem option = inOption;
#     initStyleOption(&option, index);

#     if (option.text.isEmpty()) {
#         // This is nothing this function is supposed to handle
#         return QStyledItemDelegate::sizeHint(inOption, index);
#     }

#     QTextDocument doc;
#     doc.setHtml(option.text);
#     doc.setTextWidth(option.rect.width());
#     doc.setDefaultFont(option.font);
#     doc.setDocumentMargin(0);

#     return QSize(doc.idealWidth(), doc.size().height());
# }


# Ported from Qt5 C++ code https://stackoverflow.com/a/66412883/2624876
# Unfortunately, while `completer.popup().setItemDelegate(RichTextItemDelegate())` is doing something,
# nothing is rendered in the popup. The methods `paint` and `sizeHint` don't seem to be called at all.
class RichTextItemDelegate(QStyledItemDelegate):
    def paint(self, painter: QPainter|None, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        option = QStyleOptionViewItem(option)
        self.initStyleOption(option, index)
        print("option.text???:", option.text)

        if not option.text or not painter:
            super().paint(painter, option, index)
            return

        style = (option.widget.style() if option.widget else QApplication.style()) or QStyle()

        text_option = QTextOption()
        if option.features & QStyleOptionViewItem.ViewItemFeature.WrapText:
            text_option.setWrapMode(QTextOption.WrapMode.WordWrap)
        else:
            text_option.setWrapMode(QTextOption.WrapMode.ManualWrap)
        text_option.setTextDirection(option.direction)

        doc = QTextDocument()
        doc.setDefaultTextOption(text_option)
        doc.setHtml(option.text)
        doc.setDefaultFont(option.font)
        doc.setDocumentMargin(0)
        doc.setTextWidth(option.rect.width())
        doc.adjustSize()

        if doc.size().width() > option.rect.width():
            cursor = QTextCursor(doc)
            cursor.movePosition(QTextCursor.MoveOperation.End)

            elided_postfix = "..."
            metric = QFontMetrics(option.font)
            postfix_width = metric.horizontalAdvance(elided_postfix)

            while doc.size().width() > option.rect.width() - postfix_width:
                cursor.deletePreviousChar()
                doc.adjustSize()

            cursor.insertText(elided_postfix)

        # Paint the item background (selection, hover, etc.)
        option.text = ""
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem, option, painter, option.widget)

        # Determine alignment and position
        text_rect = style.subElementRect(QStyle.SubElement.SE_ItemViewItemText, option, option.widget)
        document_size = doc.size().toSize()
        layout_rect = QStyle.alignedRect(
            Qt.LayoutDirection.LayoutDirectionAuto,
            option.displayAlignment,
            document_size,
            text_rect
        )

        painter.save()
        painter.translate(layout_rect.topLeft())
        doc.drawContents(painter, QRectF(0, 0, text_rect.width(), text_rect.height()))
        painter.restore()

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        option = QStyleOptionViewItem(option)
        self.initStyleOption(option, index)

        print("option.text??:", option.text)
        if not option.text:
            return super().sizeHint(option, index)

        doc = QTextDocument()
        doc.setHtml(option.text)
        doc.setTextWidth(option.rect.width())
        doc.setDefaultFont(option.font)
        doc.setDocumentMargin(0)

        return QSize(int(doc.idealWidth()), int(doc.size().height()))


# Old PyQt4 code, lightly edited
# class HTMLDelegate(QStyledItemDelegate):
#     def paint(self, painter: QPainter|None, option: QStyleOptionViewItem, index: QModelIndex) -> None:
#         # options = QStyleOptionViewItemV4(option)
#         # self.initStyleOption(options,index)

#         # style = QApplication.style() if options.widget is None else options.widget.style()

#         doc = QTextDocument()
#         doc.setHtml(options.text)

#         options.text = ""
#         style.drawControl(QStyle.CE_ItemViewItem, options, painter)

#         ctx = QAbstractTextDocumentLayout.PaintContext()

#         # Highlighting text if item is selected
#         #if (optionV4.state & QStyle::State_Selected)
#             #ctx.palette.setColor(QPalette::Text, optionV4.palette.color(QPalette::Active, QPalette::HighlightedText));

#         textRect = style.subElementRect(QStyle.SE_ItemViewItemText, options)
#         painter.save()
#         painter.translate(textRect.topLeft())
#         painter.setClipRect(textRect.translated(-textRect.topLeft()))
#         doc.documentLayout().draw(painter, ctx)

#         painter.restore()

#     def sizeHint(self, option, index):
#         options = QStyleOptionViewItemV4(option)
#         self.initStyleOption(options,index)

#         doc = QTextDocument()
#         doc.setHtml(options.text)
#         doc.setTextWidth(options.rect.width())
#         return QSize(doc.idealWidth(), doc.size().height())
