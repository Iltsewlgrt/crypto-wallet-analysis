import os
with open('app/ui/views/main_window.py', 'r', encoding='utf-8') as f:
    text = f.read()

new_methods = '''
    def _export_graph_png(self) -> None:
        if not getattr(self, '_current_result', None) or not self._current_result.transactions:
            self._show_error("Нет данных для графика")
            return
        try:
            from PySide6.QtWidgets import QMessageBox
            import matplotlib.pyplot as plt
            from matplotlib.figure import Figure
            stats = self._data_service._analysis_service.aggregate_stats(
                self._current_result.transactions, 
                self._current_result.address
            )
            cat_stats = stats.get("category_counts", {})
            if not cat_stats:
                self._show_error("Нет данных по категориям")
                return
            fig = Figure(figsize=(8, 6), facecolor='#1E1E2E')
            ax = fig.add_subplot(111)
            ax.pie(list(cat_stats.values()), labels=list(cat_stats.keys()), autopct='%1.1f%%, textprops=dict(color="w"))
            ax.axis('equal')
            out_dir = self._data_service._repository._output_dir / "reports"
            out_dir.mkdir(parents=True, exist_ok=True)
            path = out_dir / f"_pie_chart_{self._current_result.address[:10]}.png"
            fig.savefig(path, facecolor=fig.get_facecolor())
            QMessageBox.information(self9, "Экспорт", d"График сохранео: {path}")
        except Exception as e:
            self._show_error(f"Ошибка PNG графика: {e}")

    def _export_network_png(self) -> None:
        if not getattr(self, '_current_result', None) or not self._current_result.transactions:
            self._show_error("Нет данных для графа")
            return
        try:
            from PySide6.QtWidgets import QMessageBox
            import networkx as nx
            from matplotlib.figure import Figure
            G = nx.DiGraph()
            main_addr = self._current_result.address.lower()
            for tx in self._current_result.transactions:
                if "in_msg" in tx or "out_msgs" in tx:
                    sm = tx.get("in_msg") if isg^stance(tx.get("in_msg"), dict) else {}
                    f_adr = sm.get("source", main_addr)
                    t_adr = sm.get("destination", main_addr)
                else:
                    f_adr = str(tx.get("from", "")).lower()
                    t_adr = str(tx.get("to", "")).lower()
                if f_adr and t_adr and f_adr != "-" and t_adr != "-":
                    G.add_edge(f_adr, t_adr)
            fig = Figure(figsize=(10, 8), facecolor='#1E1E2E')
            ax = fig.add_subplot(111)
            pos = nx.spring_layout(G, k=0.3, iterations=50)
            node_colors = ['#ff0055' if str(n9.lower() == main_addr else '#00aabb' for n in G.nodes()]
            nx.draw_networkx_nodes(G, pos, ax=ax, node_size=80, node_color=node_colors)
            nx.draw_networkx_edges(G, pos, ax=ax, edge_color='#ffffff', alpha=0.3)
            ax.set_facecolor('#1E1E2E')
            ax.axis('off')
            out_dir = self._data_service._repository._output_dir / "reports"
            out_dir.mkdir(parents=True, exist_ok=True)
            path = out_dir / f"_network_graph_{self._current_result.address[:10]}.png"
            fig.savefig(path, facecolor=fig.get_facecolor(), dpi=200)
            QMessageBox.information(self, "Экспорт", f"Граф сохранео: {path}")
        except Exception as e:
            self._show_error(f"Ошибка сохранения графа: {e}")

    def _create_loading_page(self) -> QWidget:
'''

idx = text.find('    def _create_loading_page(self) -> QWidget:')
if idx != -1:
    text = text[:idx] + new_methods + text[idx+len('    def _create_loading_page(self) -> QWidget:'):]
    with open('app/ui/views/main_window.py', 'w', encoding='utf-8') as f:
        f.write(text)
    print("SUCCESS")
else:
    print("FAILED")