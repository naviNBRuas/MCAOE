from __future__ import annotations

__all__ = ["MCAOEApp"]


def __getattr__(name: str) -> type:
	if name != "MCAOEApp":
		raise AttributeError(name)

	try:
		from .app import MCAOEApp as _MCAOEApp
	except ModuleNotFoundError as exc:
		if exc.name == "textual":
			raise ModuleNotFoundError("Textual is required to launch the MCAOE UI.") from exc
		raise

	return _MCAOEApp
