# optimization

Weekly lot sizing (`weekly_model.py`), shift-level planning (`daily_model.py`), shift sequencing (`sequencing.py`), lexicographic solve (`solver.py`) and the chain weekly → shift MIP → sequencing (`planner.py`).

Constraint names in the code mirror the `\label`s of `dissertacao/ModelagemAlgebrica.tex` (`balanco`, `meta_semana`, `forma_saida`, `seq_capacidade`, ...).

## Implementation conventions

These rules handle data gaps. They are not part of the algebraic model.

- Missing cell in a setup matrix (`color_setup`, `form_setup`): full cleaning, worth the largest time registered in the same matrix. Diagonal cells are 0. See `complete_setup_matrix`.
- Machine without `initial_form`: it starts from a fictitious form `'0'`, and the first change costs the largest time of the form matrix.
- Machine without `initial_color`: the sequencing entry is a fictitious SKU `'0'`, and the first color run costs the largest time of the color matrix. After a form change the entry is empty, at cost 0.
- The shift MIP reserves that entry for a machine with a known form and an unknown color. `u_js` marks that the color is still unknown: it starts at 1 and drops after the first run or a form change. `e_js` reserves the largest color time in the capacity of a shift where `u_js` = 1 and a run happens (`cor_inicial_estado`, `cor_inicial_reserva`). The plan therefore fits once sequenced.
- Warehouse: `warehouse_capacity_kg` None means no warehouse constraint. Otherwise Omega is the larger of that capacity and the total initial stock.
- Orders past due before the horizon enter the first period. This is equivalent to an initial backlog `b_0`.
- Forbidden color transitions do not exist after the matrix is completed.
