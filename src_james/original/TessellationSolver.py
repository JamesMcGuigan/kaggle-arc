import inspect
from itertools import product

from src_james.original.GeometrySolver import GeometrySolver
from src_james.original.ZoomSolver import ZoomSolver
from src_james.original.functions import *
from src_james.original.functions import crop_inner, crop_outer



class TessellationSolver(GeometrySolver):
    verbose = True
    debug   = False
    options = {
        "preprocess": {
            "np.copy":    (np.copy, []),
            "crop_inner": (crop_inner, range(0,9)),
            "crop_outer": (crop_outer, range(0,9)),
            },
        "transform": {
            "none":              ( np.copy,      []        ),
            "flip":              ( np.flip,      [0,1]     ),
            "rot90":             ( np.rot90,     [1,2,3]   ),
            "roll":              ( np.roll,      product([-1,1],[0,1]) ),
            "swapaxes":          ( np.swapaxes,  [(0, 1)]  ),
            "rotate_loop":       ( rotate_loop,         range(-4,4) ),
            "rotate_loop_rows":  ( rotate_loop_rows,    range(-4,4) ),  # BROKEN ?
            "rotate_loop_cols":  ( rotate_loop_cols,    range(-4,4) ),  # BROKEN ?
            "flip_loop":         ( flip_loop,           range(0,2)  ),  # BROKEN ?
            "flip_loop_rows":    ( flip_loop_rows,      range(0,2)  ),  # BROKEN ?
            "flip_loop_cols":    ( flip_loop_cols,      range(0,2)  ),  # BROKEN ?
            "invert":            ( invert,              [max_color, min_color, max_color_1d, count_colors, count_squares, *range(1,9)]  ), # BROKEN
            # TODO: Invert
            },
        "query": {
            "query_true":              ( query_true,          [] ),
            "query_not_zero":          ( query_not_zero,      [] ),
            "query_max_color":         ( query_max_color,     [] ),
            "query_min_color":         ( query_min_color,     [] ),
            "query_max_color_1d":      ( query_max_color_1d,  [] ),
            "query_min_color_1d":      ( query_min_color_1d,  [] ),
            "query_count_colors":      ( query_count_colors,      [] ),
            "query_count_colors_row":  ( query_count_colors_row,  [] ),
            "query_count_colors_col":  ( query_count_colors_col,  [] ),
            "query_count_squares":     ( query_count_squares,     [] ),
            "query_count_squares_row": ( query_count_squares_row, [] ),
            "query_count_squares_col": ( query_count_squares_col, [] ),
            "query_color":             ( query_color,         range(0,10) ),  # TODO: query_max_color() / query_min_color()
            }
        }


    def detect(self, task):
        if self.is_task_shape_ratio_unchanged(task):            return False  # Use GeometrySolver
        if not self.is_task_shape_ratio_integer_multiple(task): return False  # Not a Tessalation problem
        if not all([ count_colors(spec['input']) == count_colors(spec['output']) for spec in task['train'] ]): return False  # Different colors
        if ZoomSolver().solve(task):                            return False
        #if not self.is_task_shape_ratio_consistant(task):       return False  # Some inconsistant grids are tessalations
        return True



    def loop_options(self):
        for (preprocess,p_args) in self.options['preprocess'].values():
            # print( (preprocess,p_args) )
            for p_arg in p_args or [()]:
                p_arg = make_tuple(p_arg)
                # print( (preprocess,p_args) )
                for (transform,t_args) in self.options['transform'].values():
                    for t_arg in t_args or [()]:
                        t_arg = make_tuple(t_arg)
                        for (query,q_args) in self.options['query'].values():
                            for q_arg in q_args or [()]:
                                q_arg = make_tuple(q_arg)
                                yield (preprocess, p_arg),(transform,t_arg),(query,q_arg)

    # TODO: hieraracharical nesting of solves and solutions/rules array generator
    def test(self, task):
        if task['file'] in self.cache: return True
        for (preprocess,p_arg),(transform,t_arg),(query,q_arg) in self.loop_options():
            kwargs = {
                "preprocess": preprocess,
                "p_arg":      p_arg,
                "transform":  transform,  # TODO: invert every other row | copy pattern from train outputs | extend lines
                "t_arg":      t_arg,
                "query":      query,  # TODO: max_colour limit counter
                "q_arg":      q_arg,
                }
            if self.is_lambda_valid(task, self.action, **kwargs, task=task):
                self.cache[task['file']] = kwargs
                if self.verbose: print(self.action, kwargs)
                return True
        return False


    def action(self, grid, preprocess=np.copy, p_arg=(), transform=np.copy, t_arg=(), query=query_true, q_arg=(), task=None):
        #print('action', preprocess, transform, query)
        if inspect.isgeneratorfunction(transform):
            generator = transform(grid, *t_arg)
            transform = lambda grid, *args: next(generator)

        # Some combinations of functions will throw gemoetry
        output = None
        try:
            grid    = preprocess(grid, *p_arg)
            output  = self.get_output_grid(grid, task).copy()
            ratio   = ( int(output.shape[0] / grid.shape[0]), int(output.shape[1] / grid.shape[1]) )
            (gx,gy) = grid.shape
            for x,y in product(range(ratio[0]),range(ratio[1])):
                copy = np.zeros(grid.shape)
                # noinspection PyArgumentList
                if query(grid,x%gx,y%gy, *q_arg):
                    copy = transform(grid, *t_arg)

                output[x*gx:(x+1)*gx, y*gy:(y+1)*gy] = copy
        except Exception as exception:
            if self.debug: print(exception)
        return output


    def loop_ratio(self, task):
        ratio = list(self.task_shape_ratios(task))[0]
        for i in range(int(ratio[0])):
            for j in range(int(ratio[1])):
                yield i,j


    def get_output_grid(self, grid, task):
        try:
            #print('get_output_grid(self, grid, task)', grid, task)
            for index, spec in enumerate(task['train']):
                if spec['input'] is grid:
                    return spec['output']
            else:
                # No output for tests
                ratio = list(self.task_shape_ratios(task))[0]
                ratio = list(map(int, ratio))
                shape = ( int(grid.shape[0]*ratio[0]), int(grid.shape[1]*ratio[1]) )
                return np.zeros(shape)
        except Exception as exception:
            if self.debug: print(exception)
            pass