
"""
Dennis A Simpson
University of North Carolina at Chapel Hill
450 West Drive
Chapel Hill, NC  27599

@Copyright 2021
"""

import sys
from distutils import log
from collections import defaultdict
from types import SimpleNamespace
import csv

__version__ = "0.5.0"


class TemplateErrorChecking:
    def __init__(self, input_file):
        self.stdout = sys.stdout
        self.sample_dictionary, self.args = self.parse_sample_file(input_file)
        self.pipette_info_dict = None
        self.slot_dict = None
        self.pipette_information()
        self.well_label_dict = self.well_labels()

    @staticmethod
    def parse_sample_file(input_file):
        """
        Parse TSV file
        :param input_file:
        :return:
        """
        line_num = 0
        options_dictionary = defaultdict(str)
        sample_dictionary = defaultdict(list)
        index_file = list(csv.reader(open(input_file), delimiter='\t'))

        for line in index_file:
            # Get the program linked to the template file.  Data should always be the first cell of line one.
            if line_num == 0:
                options_dictionary["Program"] = line[0]

            line_num += 1
            col_count = len(line)
            tmp_line = []
            sample_key = ""
            if col_count > 0 and "#" not in line[0] and len(line[0].split("#")[0]) > 0:
                # Skip any lines that are blank or comments.

                for i in range(6):
                    try:
                        line[i] = line[i].split("#")[0]  # Strip out end of line comments and white space.
                    except IndexError:
                        print("There is a syntax error in the TSV file on line {}, column {} "
                              .format(str(line_num), str(i)))

                        raise SystemExit(1)

                    if i == 0 and "--" in line[0]:
                        key = line[0].strip('--')
                        options_dictionary[key] = line[1]
                    elif "--" not in line[0] and int(line[0]) < 12:
                        sample_key = line[0], line[1]
                        tmp_line.append(line[i])
                if sample_key:
                    sample_dictionary[sample_key] = tmp_line

        return sample_dictionary, SimpleNamespace(**options_dictionary)

    def slot_error_check(self):
        slot_error = False
        slot_list = \
            ["Slot1", "Slot2", "Slot3", "Slot4", "Slot5", "Slot6", "Slot7", "Slot8", "Slot9", "Slot10", "Slot11"]

        slot_dict = {}
        print("Checking Labware Definitions in Slots")

        for i in range(len(slot_list)):
            labware = getattr(self.args, "{}".format(slot_list[i]))

            if labware and labware not in self.labware_slot_definitions:
                print("ERROR: Slot {} labware definition not correct.".format(slot_list[i]))
                slot_error = True
            slot_dict[str(i + 1)] = labware

        if slot_error:
            print("NOTICE: There are errors in the labware definitions.  Correct these and run again\n")
        else:
            print("\tLabware definitions in slots passed")

        self.slot_dict = slot_dict

        return slot_error

    def pipette_error_check(self):
        pipette_error = False

        log.info("Checking Pipette Definitions")
        if self.args.LeftPipette:
            pipette_error = self.pipette_definition_error_check(pipette_error, self.args.LeftPipette, "Left Pipette")
        if self.args.RightPipette:
            pipette_error = self.pipette_definition_error_check(pipette_error, self.args.RightPipette, "Right Pipette")
        if pipette_error:
            msg = "There is an error in the one of the pipette definitions"
            print("ERROR: {}".format(msg))

            return msg
        else:
            print("\tPipette definitions passed.")

        return pipette_error

    def tip_box_error_check(self):
        print("Checking Pipette Tip Box Definitions")
        pipette_tip_box_error = False
        lft_err_msg = ""
        rt_err_msg = ""

        if self.args.LeftPipette:
            pipette_tip_box_error, lft_err_msg = \
                self.pipette_tipbox_error_check(self.args.LeftPipetteTipRackSlot.split(","), pipette_tip_box_error,
                                                self.args.LeftPipette, "Left pipette labware")
        if self.args.RightPipette:
            pipette_tip_box_error, rt_err_msg = \
                self.pipette_tipbox_error_check(self.args.RightPipetteTipRackSlot.split(","), pipette_tip_box_error,
                                                self.args.RightPipette, "Right pipette labware")
        if pipette_tip_box_error:
            msg = "{}{}".format(lft_err_msg, rt_err_msg)
            print("ERROR: {}".format(msg))
            return msg
        else:
            print("\tPipette tip box definitions passed")

        return pipette_tip_box_error

    def reagent_slot_error_check(self, reagent_labware):
        msg = ""
        # Check the reagent slot and reagent wells
        if not self.args.ReagentSlot:
            msg = 'Reagent Slot definition missing.'
            print("ERROR: {}".format(msg))
            return msg
        for pipette in self.pipette_info_dict:
            if reagent_labware == self.pipette_info_dict[pipette]:
                msg = "Reagent slot contains a pipette tip box"
                print("ERROR: {}".format(msg))
                return msg
        return msg

    def generic_pcr(self):
        """
        Perform error checking on the template for the Generic PCR program.
        :return:
        """

        reagent_slot = self.args.ReagentSlot
        reagent_labware = self.slot_dict[reagent_slot]

        msg = self.reagent_slot_error_check(reagent_labware)
        if msg:
            return msg

        water_control_slot = self.args.WaterControl.split(",")[0]
        water_control_labware = self.slot_dict[water_control_slot]
        water_control_well = self.args.WaterControl.split(",")[1]

        water_control_labware_pass = False
        reagent_labware_pass = False

        for key in self.well_label_dict:
            if key in water_control_labware:
                water_control_labware_pass = True
                label_list = self.well_label_dict[key]
                if water_control_well not in label_list:
                    msg = "The well defined for the Water Control Sample is not possible for {}"\
                        .format(water_control_labware)
                    print("ERROR: {}".format(msg))
                    return msg

            if key in reagent_labware:
                reagent_labware_pass = True
                label_list = self.well_label_dict[key]
                if self.args.WaterWell not in label_list:
                    msg = "The water well definition is not possible for {}".format(reagent_labware)
                    print("ERROR: {}".format(msg))
                    return msg

                if self.args.PCR_MixWell not in label_list:
                    msg = "The well defined for the PCR Mix is not possible for {}".format(reagent_labware)
                    print("ERROR: {}".format(msg))
                    return msg

        if not water_control_labware_pass:
            print("The Water Control labware is not correctly defined.")
        if not reagent_labware_pass:
            print("ERROR: The Reagent labware is not correctly defined.")

        # Process Sample data;
        source_test = []
        dest_test = []
        for sample_key in self.sample_dictionary:
            sample_source_slot = self.sample_dictionary[sample_key][0]
            sample_source_well = self.sample_dictionary[sample_key][1]
            sample_dest_slot = self.sample_dictionary[sample_key][4]
            # sample_dest_labware = self.labware_slot_definitions[int(sample_dest_slot)]
            sample_dest_well = self.sample_dictionary[sample_key][5]
            source_test.append("{}+{}".format(sample_source_slot, sample_source_well))

            # If there are replicates a single sample can have more than one destination well.
            for well in sample_dest_well:
                dest_test.append("{}+{}".format(sample_dest_slot, well))
        for source in source_test:
            if source in dest_test:
                msg = "More than one sample share the same source and/or destinations"
                print("ERROR:  {}".format(msg))
                return msg

    def illumina_dual_indexing(self):

        reagent_slot = self.args.ReagentSlot
        reagent_labware = self.slot_dict[reagent_slot]
        msg = self.reagent_slot_error_check(reagent_labware)

        if msg:
            return msg

        for key in self.well_label_dict:
            label_list = self.well_label_dict[key]
            if key in reagent_labware:
                if self.args.WaterWell not in label_list:
                    msg = "The water well definition is not possible for {}".format(reagent_labware)
                    print("ERROR: {}".format(msg))
                    return msg

                if self.args.PCR_MixWell not in label_list:
                    msg = "The well defined for the PCR Mix is not possible for {}".format(reagent_labware)
                    print("ERROR: {}".format(msg))
                    return msg

        # Process Sample data;
        source_test = []
        dest_test = []
        for sample_key in self.sample_dictionary:
            sample_source_slot = self.sample_dictionary[sample_key][0]
            sample_source_well = self.sample_dictionary[sample_key][1]
            sample_dest_slot = self.sample_dictionary[sample_key][4]
            # sample_dest_labware = self.labware_slot_definitions[int(sample_dest_slot)]
            sample_dest_well = self.sample_dictionary[sample_key][5]
            source_test.append("{}+{}".format(sample_source_slot, sample_source_well))

            # If there are replicates a single sample can have more than one destination well.
            for well in sample_dest_well:
                dest_test.append("{}+{}".format(sample_dest_slot, well))
        for source in source_test:
            if source in dest_test:
                msg = "More than one sample share the same source and/or destinations"
                print("ERROR:  {}".format(msg))
                return msg

    @property
    def labware_slot_definitions(self):
        """
        Labware that we have on-hand.
        :return:
        """
        labware_list = [
            "opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap", "stacked_96_well", "8_well_strip_tubes_200ul",
            "opentrons_96_tiprack_10ul", "opentrons_96_tiprack_20ul", "opentrons_96_tiprack_300ul",
            "vwrscrewcapcentrifugetube5ml_15_tuberack_5000ul"]

        return labware_list

    def well_labels(self):
        """
        Create a dictionary of well labels for each loaded labware.
        :return:
        """

        def well_list(row_count, column_count):
            row_labels = \
                ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T",
                 "U", "V", "W", "X", "Y", "Z"]

            temp_list = []
            for r in range(row_count):
                for i in range(column_count):
                    temp_list.append("{}{}".format(row_labels[r], i + 1))

            return temp_list

        well_labels_dict = defaultdict(list)
        for labware in self.labware_slot_definitions:
            w96 = well_list(8, 12)
            w24 = well_list(4, 6)
            w15 = well_list(3, 5)

            if "24" in labware:
                well_labels_dict[labware] = w24
            elif "96" in labware:
                well_labels_dict[labware] = w96
            elif "_15_tuberack" in labware:

                well_labels_dict[labware] = w15
            elif len(well_labels_dict) == 0:
                msg = "Well label definitions failed.  Incorrect labware passed.  Template file is bad"
                print("ERROR:  {}".format(msg))
                return msg

        return well_labels_dict

    def pipette_information(self):
        self.pipette_info_dict = {"p10_multi": "opentrons_96_tiprack_10ul", "p10_single": "opentrons_96_tiprack_10ul",
                                  "p20_single_gen2": "opentrons_96_tiprack_20ul",
                                  "p300_single_gen2": "opentrons_96_tiprack_300ul"}

    def pipette_tipbox_error_check(self, pipette_tip_slots, error_state, pipette, msg):
        pipette_labware = self.pipette_info_dict[pipette]
        err_msg = ""
        for slot in pipette_tip_slots:
            if self.slot_dict[slot] != pipette_labware:
                err_msg = "ERROR:  {} in slot {} is not correct.".format(msg, slot)
                error_state = True
        return error_state, err_msg

    def pipette_definition_error_check(self, error_state, pipette, pipette_str):
        if pipette not in self.pipette_info_dict:
            error_state = True
            print("ERROR:  {} definition not correct".format(pipette_str))
        return error_state
