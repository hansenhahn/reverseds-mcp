"""NDS ROM filesystem and overlays served by the emulator over the control channel.

The emulator is the source of truth: the ROM header, FNT/FAT tables, overlay tables and file
contents are read with ``rom.info``/``rom.read``. Parsing stays in the domain
(`NdsFs`, `OverlayTable`); this adapter only moves bytes and detects a ROM change.
"""
import threading

from ..domain.cartfs import FileEntry, NdsFs, NdsHeader, RomInfo
from ..domain.overlays import Overlay, OverlayHit, OverlayTable
from ..application.ports import CartFs, ControlChannel, Overlays

_HEADER_SIZE = 0x200
_CORES = ("arm9", "arm7")
_READ_CHUNK = 4 * 1024 * 1024


class NdsRomError(RuntimeError):
    """Error reading or parsing the ROM loaded in the emulator."""


class ChannelRom(CartFs, Overlays):
    """Filesystem and overlays of the ROM loaded in the emulator."""

    def __init__(self, channel: ControlChannel) -> None:
        """Read the ROM from the control channel on demand.

        Parameters:
            channel (ControlChannel): A connected control channel.
        """
        self._channel = channel
        self._lock = threading.RLock()
        self._info: RomInfo | None = None
        self._fs: NdsFs | None = None
        self._overlays: dict[str, OverlayTable] = {}

    def info(self) -> RomInfo:
        """Return the identity of the loaded ROM, reloading it when it changed.

        Returns:
            RomInfo: The loaded ROM identity (``loaded=False`` when there is no cart).

        Raises:
            ControlError: If the control channel fails.
        """
        with self._lock:
            result = self._channel.call("rom.info")
            info = RomInfo(
                loaded=bool(result.get("loaded", False)),
                name=str(result.get("name") or ""),
                path=str(result.get("path") or ""),
                size=int(result.get("size") or 0),
                gamecode=str(result.get("gamecode") or ""),
                checksum=int(result.get("checksum") or 0),
            )
            if not info.loaded:
                self._info = info
                self._fs = None
                self._overlays = {}
                return info
            if info != self._info:
                self._load(info)
            return info

    def refresh(self) -> RomInfo:
        """Reload the loaded ROM when it changed and fail when there is no cart.

        Returns:
            RomInfo: The loaded ROM identity.

        Raises:
            NdsRomError: If there is no ROM loaded in the emulator.
            ControlError: If the control channel fails.
        """
        info = self.info()
        if not info.loaded:
            raise NdsRomError("nenhuma ROM carregada no emulador")
        return info

    def _load(self, info: RomInfo) -> None:
        header = NdsHeader.from_bytes(self._read(0, _HEADER_SIZE))
        fs = NdsFs.from_bytes(
            self._read(header.fnt_offset, header.fnt_size),
            self._read(header.fat_offset, header.fat_size),
        )
        overlays = {core: self._read_overlays(core, header) for core in _CORES}
        self._info = info
        self._fs = fs
        self._overlays = overlays

    def _read(self, offset: int, size: int) -> bytes:
        data = bytearray()
        while len(data) < size:
            chunk = min(_READ_CHUNK, size - len(data))
            result = self._channel.call(
                "rom.read", {"offset": offset + len(data), "size": chunk}
            )
            binary = result.get("binary")
            payload = binary.get("data") if isinstance(binary, dict) else None
            if not isinstance(payload, (bytes, bytearray)) or len(payload) != chunk:
                raise NdsRomError("resposta inválida de rom.read")
            data.extend(payload)
        return bytes(data)

    def _read_overlays(self, core: str, header: NdsHeader) -> OverlayTable:
        if core == "arm9":
            offset, size = header.arm9_overlay_offset, header.arm9_overlay_size
        else:
            offset, size = header.arm7_overlay_offset, header.arm7_overlay_size
        if size == 0:
            return OverlayTable([])
        return OverlayTable.from_bytes(self._read(offset, size), core)

    def _snapshot(self) -> tuple[NdsFs, dict[str, OverlayTable]]:
        with self._lock:
            if self._fs is None:
                info = self.info()
                if not info.loaded:
                    raise NdsRomError("nenhuma ROM carregada no emulador")
            assert self._fs is not None
            return self._fs, self._overlays

    def header(self) -> NdsHeader:
        """Return the full ROM header from the loaded ROM."""
        info = self.info()
        if not info.loaded:
            raise NdsRomError("nenhuma ROM carregada no emulador")
        return NdsHeader.from_bytes(self._read(0, _HEADER_SIZE))

    def file_count(self) -> int:
        fs, _ = self._snapshot()
        return fs.file_count()

    def files(self) -> list[FileEntry]:
        fs, _ = self._snapshot()
        return fs.files()

    def file_for_offset(self, offset: int) -> str | None:
        fs, _ = self._snapshot()
        return fs.file_for_offset(offset)

    def read_file(self, path: str) -> bytes:
        fs, _ = self._snapshot()
        span = fs.span(path)
        if span is None:
            raise NdsRomError(f"arquivo não encontrado: {path}")
        return self._read(span.start, span.size)

    def overlay_list(self, core: str) -> list[Overlay]:
        _, overlays = self._snapshot()
        if core not in overlays:
            raise NdsRomError(f"core desconhecido: {core!r} (use 'arm9' ou 'arm7')")
        return overlays[core].entries()

    def overlay_for_address(self, addr: int, core: str = "arm9") -> OverlayHit | None:
        _, overlays = self._snapshot()
        table = overlays.get(core)
        return table.for_address(addr) if table is not None else None
