from __future__ import annotations

import base64
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import streamlit.components.v1 as components

_TEXTURE_DIR = Path(__file__).resolve().parent.parent / "assets" / "textures"
_TEXTURE_FILES = {
    "earth": ("earth_blue_marble_4096.jpg", "image/jpeg"),
    "night": ("earth_night_4096.jpg", "image/jpeg"),
    "clouds": ("earth_clouds_1024.png", "image/png"),
    "normal": ("earth_normal_2048.jpg", "image/jpeg"),
    "specular": ("earth_specular_2048.jpg", "image/jpeg"),
}


def render_globe(
    position: dict[str, Any] | None,
    satellite_name: str | None,
    *,
    trajectory: list[dict[str, Any]] | None = None,
    height: int = 640,
) -> None:
    """Render a Three.js earth scene, optionally with a satellite marker."""

    payload = _build_payload(position, satellite_name, trajectory)
    components.html(_build_html(payload), height=height, scrolling=False)


def _build_payload(
    position: dict[str, Any] | None,
    satellite_name: str | None,
    trajectory: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "hasPosition": False,
        "satelliteName": satellite_name or "卫星",
        "trajectory": _sanitize_trajectory(trajectory or []),
    }

    if not position or position.get("error"):
        return payload

    try:
        latitude = float(position["latitude"])
        longitude = float(position["longitude"])
        altitude_km = float(position["altitude_km"])
    except (KeyError, TypeError, ValueError):
        return payload

    payload.update(
        {
            "hasPosition": True,
            "latitude": latitude,
            "longitude": longitude,
            "altitudeKm": altitude_km,
            "timestampUtc": str(position.get("timestamp_utc", "")),
        }
    )
    return payload


def _sanitize_trajectory(trajectory: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sanitized: list[dict[str, Any]] = []
    for point in trajectory:
        if point.get("error"):
            continue
        try:
            sanitized.append(
                {
                    "latitude": float(point["latitude"]),
                    "longitude": float(point["longitude"]),
                    "altitudeKm": float(point["altitude_km"]),
                    "timestampUtc": str(point.get("timestamp_utc", "")),
                }
            )
        except (KeyError, TypeError, ValueError):
            continue
    return sanitized


def _build_html(payload: dict[str, Any]) -> str:
    data = json.dumps(payload, ensure_ascii=False)
    textures = json.dumps(_texture_data_uris())
    return f"""
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    :root {{
      color-scheme: dark;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    html,
    body,
    #scene {{
      width: 100%;
      height: 100%;
      margin: 0;
      overflow: hidden;
      background: #05070a;
    }}
    #scene {{
      position: relative;
      min-height: 100%;
    }}
    canvas {{
      display: block;
      width: 100%;
      height: 100%;
      touch-action: none;
    }}
    .hud {{
      position: absolute;
      top: 16px;
      right: 16px;
      max-width: min(360px, calc(100% - 36px));
      padding: 12px 14px;
      border: 1px solid rgba(255, 255, 255, 0.16);
      background: rgba(6, 9, 13, 0.72);
      backdrop-filter: blur(12px);
      color: #f6f8fb;
      box-sizing: border-box;
    }}
    .status-row {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      margin-bottom: 8px;
    }}
    .status-pill {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      min-height: 22px;
      padding: 3px 8px;
      border-radius: 999px;
      font-size: 11px;
      font-weight: 700;
      line-height: 1;
      letter-spacing: 0;
    }}
    .status-pill::before {{
      content: "";
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: currentColor;
      box-shadow: 0 0 10px currentColor;
    }}
    .status-pill.waiting {{
      border: 1px solid rgba(255, 200, 87, 0.42);
      background: rgba(255, 200, 87, 0.12);
      color: #ffc857;
    }}
    .status-pill.live {{
      border: 1px solid rgba(98, 217, 143, 0.42);
      background: rgba(98, 217, 143, 0.12);
      color: #62d98f;
    }}
    .status-pill.prediction {{
      border: 1px solid rgba(255, 200, 87, 0.44);
      background: rgba(255, 200, 87, 0.14);
      color: #ffc857;
    }}
    .name {{
      margin: 0 0 8px;
      font-size: 14px;
      font-weight: 700;
      line-height: 1.25;
      letter-spacing: 0;
      overflow-wrap: anywhere;
    }}
    .meta {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 8px;
    }}
    .item {{
      min-width: 0;
    }}
    .label {{
      display: block;
      color: rgba(246, 248, 251, 0.66);
      font-size: 11px;
      line-height: 1.2;
      letter-spacing: 0;
    }}
    .value {{
      display: block;
      margin-top: 2px;
      color: #ffffff;
      font-size: 13px;
      line-height: 1.2;
      letter-spacing: 0;
      white-space: nowrap;
    }}
    .empty {{
      margin: 0;
      color: rgba(246, 248, 251, 0.76);
      font-size: 13px;
      line-height: 1.35;
      letter-spacing: 0;
    }}
    .fallback {{
      position: absolute;
      inset: 0;
      display: none;
      align-items: center;
      justify-content: center;
      padding: 24px;
      color: #f6f8fb;
      text-align: center;
      box-sizing: border-box;
    }}
    @media (max-width: 560px) {{
      #scene {{
        min-height: 100%;
      }}
      .hud {{
        top: 12px;
        right: 12px;
        left: 12px;
        max-width: none;
      }}
      .meta {{
        grid-template-columns: 1fr;
      }}
      .value {{
        white-space: normal;
      }}
    }}
  </style>
</head>
<body>
  <div id="scene">
    <div id="fallback" class="fallback">3D 地球加载失败</div>
    <div id="hud" class="hud"></div>
  </div>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
  <script>
    const DATA = {data};
    const TEXTURES = {textures};
    const container = document.getElementById("scene");
    const hud = document.getElementById("hud");
    const fallback = document.getElementById("fallback");
    const HAS_TRAJECTORY = Array.isArray(DATA.trajectory) && DATA.trajectory.length > 1;

    function formatNumber(value, digits) {{
      return Number(value).toFixed(digits);
    }}

    function renderHud() {{
      if (!DATA.hasPosition) {{
        hud.innerHTML = `
          <div class="status-row"><span class="status-pill waiting">等待数据</span></div>
          <p class="name">${{DATA.satelliteName}}</p>
          <p class="empty">等待轨道数据</p>
        `;
        return;
      }}
      const statusClass = HAS_TRAJECTORY ? "prediction" : "live";
      const statusText = HAS_TRAJECTORY ? "预测" : "数据";
      hud.innerHTML = `
        <div class="status-row"><span class="status-pill ${{statusClass}}">${{statusText}}</span></div>
        <p class="name">${{DATA.satelliteName}}${{HAS_TRAJECTORY ? " 预测位置" : ""}}</p>
        <div class="meta">
          <div class="item"><span class="label">纬度</span><span class="value">${{formatNumber(DATA.latitude, 2)}}°</span></div>
          <div class="item"><span class="label">经度</span><span class="value">${{formatNumber(DATA.longitude, 2)}}°</span></div>
          <div class="item"><span class="label">高度</span><span class="value">${{formatNumber(DATA.altitudeKm, 1)}} km</span></div>
        </div>
      `;
    }}

    function latLonToVector3(latDeg, lonDeg, radius) {{
      const lat = THREE.MathUtils.degToRad(latDeg);
      const lon = THREE.MathUtils.degToRad(lonDeg);
      const cosLat = Math.cos(lat);
      return new THREE.Vector3(
        radius * cosLat * Math.sin(lon),
        radius * Math.sin(lat),
        radius * cosLat * Math.cos(lon)
      );
    }}

    function yawForLongitude(lonDeg) {{
      return -THREE.MathUtils.degToRad(lonDeg) + 0.28;
    }}

    function init() {{
      renderHud();
      if (!window.THREE) {{
        fallback.style.display = "flex";
        return;
      }}

      const scene = new THREE.Scene();
      scene.fog = new THREE.FogExp2(0x05070a, 0.035);

      const camera = new THREE.PerspectiveCamera(42, container.clientWidth / container.clientHeight, 0.1, 100);
      camera.position.set(0, 0.12, 3.72);

      const renderer = new THREE.WebGLRenderer({{ antialias: true, alpha: false, preserveDrawingBuffer: true }});
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
      renderer.setSize(container.clientWidth, container.clientHeight);
      renderer.setClearColor(0x05070a, 1);
      container.insertBefore(renderer.domElement, container.firstChild);

      const textureLoader = new THREE.TextureLoader();
      const maxAnisotropy = renderer.capabilities.getMaxAnisotropy();
      function loadTexture(key) {{
        const texture = textureLoader.load(TEXTURES[key]);
        texture.anisotropy = maxAnisotropy;
        return texture;
      }}

      scene.add(new THREE.AmbientLight(0x73889f, 0.34));
      const keyLight = new THREE.DirectionalLight(0xffffff, 1.85);
      keyLight.position.set(4.6, 2.1, 4.8);
      scene.add(keyLight);
      const rimLight = new THREE.DirectionalLight(0x68cfff, 0.42);
      rimLight.position.set(-4, 0.8, -2.5);
      scene.add(rimLight);

      const earthGroup = new THREE.Group();
      const fixedAxisTilt = THREE.MathUtils.degToRad(-10);
      earthGroup.rotation.x = fixedAxisTilt;
      scene.add(earthGroup);

      const earthGeometry = new THREE.SphereGeometry(1, 96, 96);
      const earthMaterial = new THREE.MeshPhongMaterial({{
        map: loadTexture("earth"),
        normalMap: loadTexture("normal"),
        normalScale: new THREE.Vector2(0.08, 0.08),
        specularMap: loadTexture("specular"),
        specular: new THREE.Color(0x1d4b64),
        shininess: 12,
      }});
      earthGroup.add(new THREE.Mesh(earthGeometry, earthMaterial));

      const nightMesh = new THREE.Mesh(
        new THREE.SphereGeometry(1.003, 96, 96),
        new THREE.MeshBasicMaterial({{
          map: loadTexture("night"),
          transparent: true,
          opacity: 0.24,
          blending: THREE.AdditiveBlending,
          depthWrite: false,
        }})
      );
      earthGroup.add(nightMesh);

      const cloudMesh = new THREE.Mesh(
        new THREE.SphereGeometry(1.012, 96, 96),
        new THREE.MeshLambertMaterial({{
          map: loadTexture("clouds"),
          transparent: true,
          opacity: 0.36,
          depthWrite: false,
        }})
      );
      earthGroup.add(cloudMesh);

      const atmosphere = new THREE.Mesh(
        new THREE.SphereGeometry(1.035, 96, 96),
        new THREE.MeshBasicMaterial({{
          color: 0x5fbfff,
          transparent: true,
          opacity: 0.08,
          side: THREE.BackSide,
        }})
      );
      earthGroup.add(atmosphere);

      const starGeometry = new THREE.BufferGeometry();
      const starPositions = [];
      for (let i = 0; i < 850; i += 1) {{
        const radius = 7 + Math.random() * 7;
        const theta = Math.random() * Math.PI * 2;
        const phi = Math.acos(2 * Math.random() - 1);
        starPositions.push(
          radius * Math.sin(phi) * Math.cos(theta),
          radius * Math.sin(phi) * Math.sin(theta),
          radius * Math.cos(phi)
        );
      }}
      starGeometry.setAttribute("position", new THREE.Float32BufferAttribute(starPositions, 3));
      scene.add(new THREE.Points(starGeometry, new THREE.PointsMaterial({{ color: 0xffffff, size: 0.014, opacity: 0.75, transparent: true }})));

      let marker = null;
      let markerHalo = null;
      let startMarker = null;
      let pathLine = null;
      if (HAS_TRAJECTORY) {{
        const pathPoints = DATA.trajectory.map((point) => latLonToVector3(point.latitude, point.longitude, 1.026));
        pathLine = new THREE.Line(
          new THREE.BufferGeometry().setFromPoints(pathPoints),
          new THREE.LineBasicMaterial({{ color: 0x35d3ff, transparent: true, opacity: 0.92 }})
        );
        earthGroup.add(pathLine);

        startMarker = new THREE.Mesh(
          new THREE.SphereGeometry(0.014, 18, 18),
          new THREE.MeshBasicMaterial({{ color: 0x35d3ff }})
        );
        startMarker.position.copy(pathPoints[0]);
        earthGroup.add(startMarker);
      }}

      if (DATA.hasPosition) {{
        const surface = latLonToVector3(DATA.latitude, DATA.longitude, 1.006);
        const satelliteRadius = 1.14 + Math.min(Math.max(DATA.altitudeKm / 6371, 0.02), 0.18);
        const satellite = latLonToVector3(DATA.latitude, DATA.longitude, satelliteRadius);

        const lineGeometry = new THREE.BufferGeometry().setFromPoints([surface, satellite]);
        const line = new THREE.Line(
          lineGeometry,
          new THREE.LineBasicMaterial({{ color: 0xffc857, transparent: true, opacity: 0.82 }})
        );
        earthGroup.add(line);

        marker = new THREE.Mesh(
          new THREE.SphereGeometry(0.025, 24, 24),
          new THREE.MeshBasicMaterial({{ color: 0xffc857 }})
        );
        marker.position.copy(satellite);
        earthGroup.add(marker);

        markerHalo = new THREE.Mesh(
          new THREE.SphereGeometry(0.054, 32, 32),
          new THREE.MeshBasicMaterial({{ color: 0xffc857, transparent: true, opacity: 0.18 }})
        );
        markerHalo.position.copy(satellite);
        earthGroup.add(markerHalo);

        earthGroup.rotation.x = fixedAxisTilt;
        earthGroup.rotation.y = yawForLongitude(DATA.longitude);
      }} else {{
        earthGroup.rotation.x = fixedAxisTilt;
        earthGroup.rotation.y = -0.55;
      }}

      const drag = {{
        active: false,
        x: 0,
      }};

      renderer.domElement.addEventListener("pointerdown", (event) => {{
        drag.active = true;
        drag.x = event.clientX;
        renderer.domElement.setPointerCapture(event.pointerId);
      }});
      renderer.domElement.addEventListener("pointermove", (event) => {{
        if (!drag.active) return;
        const dx = event.clientX - drag.x;
        drag.x = event.clientX;
        earthGroup.rotation.y += dx * 0.006;
        earthGroup.rotation.x = fixedAxisTilt;
      }});
      renderer.domElement.addEventListener("pointerup", (event) => {{
        drag.active = false;
        try {{
          renderer.domElement.releasePointerCapture(event.pointerId);
        }} catch (error) {{}}
      }});

      const clock = new THREE.Clock();
      function animate() {{
        const elapsed = clock.getElapsedTime();
        if (!drag.active && !DATA.hasPosition) {{
          earthGroup.rotation.y += 0.0012;
        }}
        earthGroup.rotation.x = fixedAxisTilt;
        cloudMesh.rotation.y += 0.00032;
        if (pathLine) {{
          pathLine.material.opacity = 0.72 + Math.sin(elapsed * 2.2) * 0.16;
        }}
        if (startMarker) {{
          startMarker.scale.setScalar(1 + Math.sin(elapsed * 3.2) * 0.10);
        }}
        if (marker) {{
          marker.scale.setScalar(1 + Math.sin(elapsed * 4) * 0.13);
        }}
        if (markerHalo) {{
          markerHalo.scale.setScalar(1.18 + Math.sin(elapsed * 3) * 0.22);
        }}
        renderer.render(scene, camera);
        requestAnimationFrame(animate);
      }}
      animate();

      const resizeObserver = new ResizeObserver(() => {{
        const width = container.clientWidth;
        const height = container.clientHeight;
        camera.aspect = width / height;
        camera.updateProjectionMatrix();
        renderer.setSize(width, height);
      }});
      resizeObserver.observe(container);
    }}

    init();
  </script>
</body>
</html>
"""


@lru_cache(maxsize=1)
def _texture_data_uris() -> dict[str, str]:
    textures: dict[str, str] = {}
    for key, (filename, mime_type) in _TEXTURE_FILES.items():
        path = _TEXTURE_DIR / filename
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        textures[key] = f"data:{mime_type};base64,{encoded}"
    return textures
