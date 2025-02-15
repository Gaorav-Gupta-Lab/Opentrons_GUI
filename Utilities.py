"""
Functions common for all robot programs.

Dennis Simpson
University of North Carolina at Chapel Hill
Chapel Hill NC, 27599

@copyright 2025

"""
import csv
import math
import os
from collections import defaultdict
from types import SimpleNamespace
# import Tool_Box as ToolBox

__version__ = "2.0.0a"


def plate_layout(labware):
    """
    Define the destination layout for the reactions.  Can be 96-well plate or 8-well strip tubes
    :param labware:
    :return:
    """

    layout_data = defaultdict(list)
    column_index = []
    if labware == "384_ABI":
        for k in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L']:
            layout_data[k] = \
                ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '',
                 '', '', '', '', '', '', '']
        for i in range(32):
            column_index.append(i+1)

    elif labware == "8_well_strip_tubes_200ul":
        for k in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']:
            layout_data[k] = ['', '', '', '', '', '', '', '', '', '', '', '']
        column_index = [1, 3, 5, 7, 9, 11, 12]
    '''
    if labware == "stacked_96_well" or labware == "96-TipBox" or labware == "bigwell_96_tuberack_200ul_dilution_tube" \
            or labware == "biorad_ddpcr_96_wellplate_100ul" or labware == "biorad_hardshell_96_wellplate_150ul":
    '''

    if "96" in labware or "ddpcr_plate" in labware:
        for k in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']:
            layout_data[k] = ['', '', '', '', '', '', '', '', '', '', '', '']
        for i in range(12):
            column_index.append(i+1)

    rows = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
    plate_layout_by_column = []
    for i in column_index:
        for row in rows:
            plate_layout_by_column.append("{}{}".format(row, i))

    return plate_layout_by_column, layout_data


def labware_cone_volume(args, labware_name):
    """
    Based on the labware and reservoir return the volume at which the cylinder shape transitions to the conical shape.
    @param args:
    @param labware_name:
    @return:
    """
    cone_vol = 200
    labware = getattr(args, "Slot{}".format(str(labware_name)[-1:]))

    if "e5ml_" in labware:
        cone_vol = 1200

    elif"1.5ml_24" in labware:
        cone_vol = 450

    return cone_vol


def res_tip_height(res_vol, well_dia, cone_vol, bottom_offset):
    """
    Calculate the height of the liquid in a reservoir and return the value to set the pipette tip height.
    This works for both conical shapes and cylinders.
    @param bottom_offset:
    @param res_vol:
    @param well_dia:
    @param cone_vol:
    @return:
    """
    if res_vol > cone_vol:
        cone_height = (3*cone_vol/(math.pi*((well_dia/2)**2)))
        height = ((res_vol-cone_vol)/(math.pi*((well_dia/2)**2)))-5+cone_height
    else:
        height = (3*res_vol/(math.pi*((well_dia/2)**2)))-3

    if height < 3:
        height = bottom_offset

    return round(height, 1)


def parse_sample_template(input_file):
    """
    Parse the TSV file and return data objects to run def.
    :param input_file:
    :return:
    """
    line_num = 0
    options_dictionary = defaultdict(str)
    sample_dictionary = defaultdict(list)
    template_file = list(csv.reader(open(input_file), delimiter='\t'))
    for line in template_file:
        if line_num == 0:
            options_dictionary["Version"] = line[1]
            options_dictionary["Template"] = line[0].strip("#")
        line_num += 1

        # Skip any lines that are blank or comments.
        if bool(line[0]) and "#" not in line[0]:
            if "--" in line[0]:
                key = line[0].strip('--')

                if "Target_" in key:
                    key_value = (line[1], line[2], line[3])
                else:
                    key_value = line[1]

                options_dictionary[key] = key_value

            else:
                sample_key = line[0], line[1]
                sample_dictionary[sample_key] = line

    return sample_dictionary, SimpleNamespace(**options_dictionary)


def initialize_system(ctx):
    # TSV file location on OT-2
    tsv_file_path = "{0}var{0}lib{0}jupyter{0}notebooks{0}ProcedureFile.tsv".format(os.sep)
    if not os.path.isfile(tsv_file_path):
        # Temp TSV file location on Windows Computers for simulation
        tsv_file_path = "C:{0}Users{0}{1}{0}Documents{0}TempTSV.tsv".format(os.sep, os.getlogin())

    sample_parameters, args = parse_sample_template(tsv_file_path)
    labware_dict, slot_dict, left_tiprack_list, right_tiprack_list = labware_parsing(args, ctx)

    # Pipettes
    left_pipette = ctx.load_instrument(args.LeftPipette, 'left', tip_racks=left_tiprack_list)
    right_pipette = ctx.load_instrument(args.RightPipette, 'right', tip_racks=right_tiprack_list)

    # Set the location of the first tip in box.
    left_pipette.starting_tip = left_tiprack_list[0].wells_by_name()[args.LeftPipetteFirstTip.upper()]
    right_pipette.starting_tip = right_tiprack_list[0].wells_by_name()[args.RightPipetteFirstTip.upper()]

    return args, tsv_file_path, sample_parameters, labware_dict, left_tiprack_list, right_tiprack_list, left_pipette, right_pipette, left_pipette.starting_tip, right_pipette.starting_tip


def labware_parsing(args, ctx):
    # Extract Slot information
    slot_list = ["Slot1", "Slot2", "Slot3", "Slot4", "Slot5", "Slot6", "Slot7", "Slot8", "Slot9", "Slot10", "Slot11"]
    labware_dict = {}
    slot_dict = {}
    tipbox_dict = \
        {"p10_multi": "opentrons_96_tiprack_10ul", "p10_single": "opentrons_96_tiprack_10ul",
         "p20_single_gen2": ["opentrons_96_tiprack_20ul", "opentrons_96_filtertiprack_20ul"],
         "p300_single_gen2": ["opentrons_96_tiprack_300ul", "opentrons_96_filtertiprack_300ul"]}
    # Pipette Tip Boxes
    left_tiprack_list = []
    right_tiprack_list = []
    for i in range(len(slot_list)):
        labware = getattr(args, "{}".format(slot_list[i]))
        if labware:
            slot_dict[str(i + 1)] = labware
            labware_dict[str(i + 1)] = ctx.load_labware(labware, str(i + 1))
            if labware in tipbox_dict[args.LeftPipette]:
                left_tiprack_list.append(labware_dict[str(i + 1)])
            elif labware in tipbox_dict[args.RightPipette]:
                right_tiprack_list.append(labware_dict[str(i + 1)])

    return labware_dict, slot_dict, left_tiprack_list, right_tiprack_list


def load_tipracks(protocol, tiprack_list, labware_dict):
    """
    Creates a list of the pipette tip labware.
    @param protocol:
    @param tiprack_list:
    @param labware_dict:
    @return:
    """
    tiprack_labware = []
    for slot in tiprack_list:
        if slot not in protocol.loaded_labwares:
            tiprack_labware.append(labware_dict[str(slot)])
    return tiprack_labware


def pipette_selection(left_pipette, right_pipette, volume):
    """
    Function to select pipette based on expected volumes.  Will also adjust volume is pipette needs to pick up >1x
    @param left_pipette:
    @param right_pipette:
    @param volume:
    @return:
    """
    loop = 1
    pipette = ""
    if volume > 20 and "P300 Single-Channel GEN2" in str(right_pipette):
        pipette = right_pipette
    elif volume <= 20 and "P20 Single-Channel GEN2" in str(left_pipette):
        pipette = left_pipette
    elif volume < 10 and "P10 Single-Channel GEN1" in str(left_pipette):
        pipette = left_pipette
    elif volume < 10 and "P10 Single-Channel GEN1" in str(right_pipette):
        pipette = right_pipette
    elif 10 <= volume <= 20 and "P10 Single-Channel GEN1" in str(left_pipette):
        pipette = left_pipette
        volume = volume * 0.5
        loop = 2
    elif 10 <= volume <= 20 and "P10 Single-Channel GEN1" in str(right_pipette):
        pipette = right_pipette
        volume = volume * 0.5
        loop = 2

    return pipette, loop, round(volume, 1)


def build_labware_dict(protocol, sample_parameters, slot_dict):
    sample_reagent_labware_dict = {}
    for key in sample_parameters:
        sample_slot = sample_parameters[key][0]
        sample_dest_slot = sample_parameters[key][5]

        if sample_dest_slot not in sample_reagent_labware_dict:
            sample_reagent_labware_dict[sample_dest_slot] = \
                protocol.load_labware(slot_dict[sample_dest_slot], sample_dest_slot)

        if sample_slot not in sample_reagent_labware_dict:
            sample_reagent_labware_dict[sample_slot] = protocol.load_labware(slot_dict[sample_slot], sample_slot)

    return sample_reagent_labware_dict


def calculate_volumes(args, sample_concentration, template_in_rxn, sample_name=None, slot_dict=None):
    """
    Calculates volumes for dilution and distribution of sample.
    Returns a list of tuples consisting of
    (uL of sample to dilute, uL of water for dilution), (uL of diluted sample in reaction, uL of water in reaction)
    :param slot_dict:
    :param sample_name:
    :param args:
    :param sample_concentration:
    :param template_in_rxn:
    :return:
    """

    max_template_vol = round(float(args.PCR_Volume)-float(args.MasterMixPerRxn), 1)
    msg = ""
    # If at least 2 uL of sample is needed then no dilution is necessary
    if template_in_rxn/sample_concentration >= 2:
        sample_vol = round(template_in_rxn/sample_concentration, 2)
        return sample_vol, 0, 0, max_template_vol-sample_vol, max_template_vol, msg

    # This will test a series of dilutions up to a 1:200.
    for i in range(50):
        dilution = (i+1)*2
        diluted_dna_conc = sample_concentration/dilution

        # Want to pipette at least 2 uL of diluted sample per well
        if 2 < template_in_rxn/diluted_dna_conc <= max_template_vol:
            diluted_sample_vol = round(template_in_rxn/diluted_dna_conc, 2)
            reaction_water_vol = max_template_vol-diluted_sample_vol

            if not args.DilutionPlateSlot:
                msg += "Dilutions are required but no Slot was defined for them."
            else:
                try:
                    slot_dict[args.DilutionPlateSlot]
                except KeyError:
                    msg += "Dilution Labware required for Slot {}".format(args.DilutionPlateSlot)

            return 1, dilution - 1, diluted_sample_vol, reaction_water_vol, max_template_vol, msg

    msg += "{} is too concentrated for Douglass to dilute.".format(sample_name)
    return "", "", "", "", "", msg


def dispensing_loop(args, loop_count, pipette, source_location, destination_location, volume, NewTip, MixReaction,
                    touch=False, MixVolume=None):
    """
    Generic function to dispense material into designated well.
    @param MixVolume:
    @param args:
    @param loop_count:
    @param pipette:
    @param source_location:
    @param destination_location:
    @param volume:
    @param NewTip:
    @param MixReaction:
    @param touch:
    @return:
    """
    def tip_touch():
        pipette.touch_tip(radius=0.75, v_offset=-8)

    if NewTip:
        if pipette.has_tip:
            pipette.drop_tip()

    if not pipette.has_tip:
        pipette.pick_up_tip()

    while loop_count > 0:
        pipette.aspirate(volume, source_location, rate=0.75)

        if touch:
            tip_touch()

        pipette.dispense(volume, destination_location, rate=0.75)
        loop_count -= 1

        if not MixReaction:
            pipette.blow_out()
            if touch:
                tip_touch()

    if MixReaction:
        v = float(args.PCR_Volume)
        if MixVolume:
            v = MixVolume
        pipette.mix(repetitions=4, volume=v*0.65, rate=2.0)
        pipette.blow_out()
        tip_touch()

    if NewTip:
        pipette.drop_tip()

    return pipette


def distribute_reagents(pipette, source_well, destination_wells, dispense_vol):
    """
    This is not used in the Error Checking Routine.
    Dispense master mix using the distribute function.
    @param pipette:
    @param source_well:
    @param destination_wells:
    @param dispense_vol:
    """
    p20_default_rate = 7.56
    p300_default_rate = 92.86

    if "P300 Single-Channel GEN2" in str(pipette):
        default_rate = p300_default_rate
    elif "P20 Single-Channel GEN2" in str(pipette):
        default_rate = p20_default_rate

    pipette.flow_rate.aspirate = 30
    pipette.flow_rate.dispense = 10

    pipette.distribute(volume=dispense_vol, source=source_well, dest=destination_wells,
                       touch_tip=True, blow_out=True, disposal_volume=1, blowout_location='source well')

    pipette.flow_rate.aspirate = default_rate
    pipette.flow_rate.dispense = default_rate

