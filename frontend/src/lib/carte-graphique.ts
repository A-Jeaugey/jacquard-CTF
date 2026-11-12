// La maquette en volume (lib/maquette3d.ts) demande WebGL 2 et une vraie carte graphique : un
// rendu émulé par le processeur la dessinerait image par image. Sans cela, le plan à plat.

let reponse: boolean | null = null;

export function carteGraphique(): boolean {
  if (reponse !== null) return reponse;
  try {
    const gl = document.createElement("canvas").getContext("webgl2");
    if (!gl) return (reponse = false);
    const info = gl.getExtension("WEBGL_debug_renderer_info");
    const nom = info ? String(gl.getParameter(info.UNMASKED_RENDERER_WEBGL)) : "";
    gl.getExtension("WEBGL_lose_context")?.loseContext();
    return (reponse = !/swiftshader|llvmpipe|software|basic render/i.test(nom));
  } catch {
    return (reponse = false);
  }
}
