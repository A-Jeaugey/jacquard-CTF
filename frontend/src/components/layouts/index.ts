// Layouts de tableau. « grid » et « list » sont intégrés ; les layouts « image-map » sont
// déclarés par le thème du pack (theme/theme.yml) et rendus par ImageMapBoard.

import type { Component } from "svelte";

import type { BoardData } from "../../lib/types";
import GridBoard from "./GridBoard.svelte";
import ListBoard from "./ListBoard.svelte";

export type BoardLayout = Component<{ data: BoardData; onOpen: (id: string) => void }>;

const builtin: Record<string, BoardLayout> = {
  grid: GridBoard,
  list: ListBoard,
};

export function getLayout(id: string | undefined): BoardLayout {
  return (id && builtin[id]) || GridBoard;
}

export { default as ImageMapBoard } from "./ImageMapBoard.svelte";
