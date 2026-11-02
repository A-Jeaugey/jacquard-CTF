// Registre des layouts de tableau. Le pack choisit son layout par identifiant
// (`board.layout` dans event.yml). Les prochains layouts (`list`, `image-map`,
// Web Components fournis par le pack) s'ajouteront ici.

import type { Component } from "svelte";

import type { BoardData } from "../../lib/types";
import GridBoard from "./GridBoard.svelte";

export type BoardLayout = Component<{ data: BoardData; onOpen: (id: string) => void }>;

const layouts: Record<string, BoardLayout> = {
  grid: GridBoard,
};

export function getLayout(id: string | undefined): BoardLayout {
  return (id && layouts[id]) || GridBoard;
}
