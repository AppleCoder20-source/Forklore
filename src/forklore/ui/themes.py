"""Color themes for Forklore's UI.

Each theme is a dict of color values the app injects as CSS. To add a theme,
copy a block and change the hex values. The first key is the default (the app
uses index 0). Keys:
  bg            page background
  sidebar       sidebar background
  text          brand text + input text
  btn           button background
  btn_hover     button hover background
  btn_text      button text
  input_bg      text-input background
  input_border  text-input border
  tagline       muted tagline text
"""

THEMES = {
    "Cool Slate": {
        "bg": "#E7EBF0", "sidebar": "#DCE2EA", "text": "#26215C",
        "btn": "#185FA5", "btn_hover": "#0C447C", "btn_text": "white",
        "input_bg": "white", "input_border": "#B5D4F4", "tagline": "#5F5E5A",
    },
    "Cream": {
        "bg": "#F3EFE7", "sidebar": "#EDE8DE", "text": "#2C2C2A",
        "btn": "#2C2C2A", "btn_hover": "#444441", "btn_text": "white",
        "input_bg": "white", "input_border": "#D3D1C7", "tagline": "#888780",
    },
    "Fresh Green": {
        "bg": "#EAF3DE", "sidebar": "#DDEBCB", "text": "#27500A",
        "btn": "#639922", "btn_hover": "#3B6D11", "btn_text": "white",
        "input_bg": "white", "input_border": "#C0DD97", "tagline": "#5F5E5A",
    },
    "Soft Sage": {
        "bg": "#E8EDE6", "sidebar": "#DCE4DA", "text": "#2C2C2A",
        "btn": "#0F6E56", "btn_hover": "#085041", "btn_text": "white",
        "input_bg": "white", "input_border": "#9FE1CB", "tagline": "#5F5E5A",
    },
    "Berry": {
        "bg": "#FBEAF0", "sidebar": "#F4D7E1", "text": "#72243E",
        "btn": "#D4537E", "btn_hover": "#993556", "btn_text": "white",
        "input_bg": "white", "input_border": "#F4C0D1", "tagline": "#5F5E5A",
    },
    "Dark": {
        "bg": "#1E1E1C", "sidebar": "#2C2C2A", "text": "#F3EFE7",
        "btn": "#F3EFE7", "btn_hover": "#D3D1C7", "btn_text": "#1E1E1C",
        "input_bg": "#2C2C2A", "input_border": "#444441", "tagline": "#B4B2A9",
    },
    "Ocean": {
        "bg": "#E1F5EE", "sidebar": "#CFEDE2", "text": "#04342C",
        "btn": "#1D9E75", "btn_hover": "#0F6E56", "btn_text": "white",
        "input_bg": "white", "input_border": "#9FE1CB", "tagline": "#5F5E5A",
    },
    "Sunset": {
        "bg": "#FAECE7", "sidebar": "#F5D8CD", "text": "#4A1B0C",
        "btn": "#D85A30", "btn_hover": "#993C1D", "btn_text": "white",
        "input_bg": "white", "input_border": "#F5C4B3", "tagline": "#5F5E5A",
    },
    "Lavender": {
        "bg": "#EEEDFE", "sidebar": "#DEDCFA", "text": "#26215C",
        "btn": "#7F77DD", "btn_hover": "#534AB7", "btn_text": "white",
        "input_bg": "white", "input_border": "#CECBF6", "tagline": "#5F5E5A",
    },
    "Mocha": {
        "bg": "#EFE7E2", "sidebar": "#E4D6CD", "text": "#4A1B0C",
        "btn": "#712B13", "btn_hover": "#4A1B0C", "btn_text": "white",
        "input_bg": "white", "input_border": "#D3D1C7", "tagline": "#5F5E5A",
    },
    "Midnight Blue": {
        "bg": "#042C53", "sidebar": "#0C447C", "text": "#E6F1FB",
        "btn": "#85B7EB", "btn_hover": "#B5D4F4", "btn_text": "#042C53",
        "input_bg": "#0C447C", "input_border": "#185FA5", "tagline": "#85B7EB",
    },
    "Mint": {
        "bg": "#E1F5EE", "sidebar": "#CFEDE2", "text": "#085041",
        "btn": "#5DCAA5", "btn_hover": "#1D9E75", "btn_text": "#04342C",
        "input_bg": "white", "input_border": "#9FE1CB", "tagline": "#5F5E5A",
    },
    "Classic Green": {
        "bg": "#FFFFFF", "sidebar": "#F1EFE8", "text": "#0F6E56",
        "btn": "#1D9E75", "btn_hover": "#0F6E56", "btn_text": "white",
        "input_bg": "white", "input_border": "#D3D1C7", "tagline": "#888780",
    },
}