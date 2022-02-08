Adding multi-results

Scan.py
1. set self.nresults
2. set self.result_names
3. Add self._measure_results
   - new do_measure method
4. _data array needs i_result index
5. _calculate needs updating
6. Add i_result argument to ScanModel::mutate_datsets_calc
7. ScanModel::means attribute needs i_result index
8. Need examples for multi-results
   - Also examples that include how to use calculate with multiple results
9. FitGuess class needs i_result attribute
10. Scan::_get_guess() needs i_result argument

ScanModel.py
1. mutate_datasets() needs updating
2. dataset array structure needs updasting
   - datasets are now stored with i_result index
3. mutate_datasets_calc() needs i_result argument
4. calculate() callback needs an i_result argument (this is not in artiq_ions)