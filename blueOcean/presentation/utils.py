import re
import flet as ft

BASE64_IMAGE_URL_PATTERN = re.compile(
    r"!\[[^\]]*\]\((data:image/[^;]+;base64,[^)]+)\)",
    re.DOTALL,
)


def parse_with_base64_images_markdown(content: str) -> ft.Control:
    parts: list[ft.Control] = []
    last_index = 0
    for match in BASE64_IMAGE_URL_PATTERN.finditer(content):
        start, end = match.span()
        if start > last_index:
            parts.append(
                ft.Markdown(
                    content[last_index:start],
                    extension_set=ft.MarkdownExtensionSet.GITHUB_FLAVORED,
                    code_theme=ft.MarkdownCodeTheme.DARK,
                )
            )
        data_url = match.group(1)
        base64_data = data_url.split(",", 1)[1]
        parts.append(ft.Image(src_base64=base64_data))
        last_index = end

    if last_index < len(content):
        parts.append(
            ft.Markdown(
                content[last_index:],
                extension_set=ft.MarkdownExtensionSet.GITHUB_FLAVORED,
                code_theme=ft.MarkdownCodeTheme.DARK,
            )
        )

    return ft.Column(parts, expand=True, scroll=ft.ScrollMode.AUTO)
