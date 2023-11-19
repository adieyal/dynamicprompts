from __future__ import annotations

import logging

import pyparsing as pp
import re

from dynamicprompts.commands import LiteralCommand, VariantCommand, VariantOption, WildcardCommand
from dynamicprompts.parser.parse import parse, _configure_variable_access, _configure_wildcard, _parse_variable_access_command
from dynamicprompts.sampling_context import SamplingContext
from dynamicprompts.sampling_result import SamplingResult
from dynamicprompts.types import ResultGen

logger = logging.getLogger(__name__)


def wildcard_to_variant(
    command: WildcardCommand,
    *,
    context: SamplingContext,
    min_bound=1,
    max_bound=1,
    separator=",",
) -> VariantCommand:
    command = replace_wildcard_variables(command=command, context=context)
    values = context.wildcard_manager.get_values(command.wildcard)
    min_bound = min(min_bound, len(values))
    max_bound = min(max_bound, len(values))

    variant_options = [
        VariantOption(parse(v, parser_config=context.parser_config))
        for v in values.iterate_string_values_weighted()
    ]

    wildcard_variant = VariantCommand(
        variant_options,
        min_bound,
        max_bound,
        separator,
        command.sampling_method,
    )
    return wildcard_variant


def get_wildcard_not_found_fallback(
    command: WildcardCommand,
    context: SamplingContext,
) -> ResultGen:
    """
    Logs a warning, then infinitely yields the wrapped wildcard.
    """
    logger.warning(f"No values found for wildcard {command.wildcard}")
    wrapped_wildcard = context.wildcard_manager.to_wildcard(command.wildcard)
    res = SamplingResult(text=wrapped_wildcard)
    while True:
        yield res

def replace_wildcard_variables(
    command: WildcardCommand, 
    *, 
    context: SamplingContext,
) -> WildcardCommand:    
    prompt = pp.SkipTo(context.parser_config.variable_end)
    variable_access = _configure_variable_access(
        parser_config=context.parser_config,
        prompt=prompt
    )
    variable_access.set_parse_action(_variable_replacement(context.variables))

    wildcard_path_re = r"((?!" + re.escape(context.parser_config.wildcard_wrap) + r")[^(${}#])+"
    wildcard_path = pp.Regex(wildcard_path_re).leave_whitespace()
    wildcard = pp.Combine(pp.OneOrMore(variable_access | wildcard_path))("path")
   
    wildcard_result = wildcard.parse_string(command.wildcard)

    return WildcardCommand(wildcard="".join(wildcard_result), sampling_method=command.sampling_method, variables=command.variables)
    
def _variable_replacement(variables: dict):
    def var_replace(string, location, token):
        if (isinstance(token, pp.ParseResults)):
            var_parts = token[0].as_dict()
            var_name = var_parts.get("name")
            if (var_name != None):
                var_name = var_name.strip()

            default = var_parts.get("default")
            if (default != None):
                default = default.strip()
            
        else:
            var_name = token
        
        variable = None
        if (var_name != None):

          variable = variables.get(var_name)

          if (isinstance(variable, LiteralCommand)):
              variable = variable.literal
        return variable or default or var_name
    return var_replace    